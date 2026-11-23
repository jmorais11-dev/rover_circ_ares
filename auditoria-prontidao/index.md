# Auditoria de Prontidão — Lançamento e Bancada


> O que falta no repositório para ligar o rover real com segurança e para os testes de bancada, comparado aos requisitos do CIRC.


{{< toc >}}

Auditoria feita em **16/11/2026** sobre o `main` do repositório. Ela responde a duas
perguntas:

1. **Lançamento:** dá para ligar, inicializar e operar o rover real de forma segura e
   reproduzível?
2. **Bancada:** dá para testar cada subsistema sozinho e depois todos juntos, antes de
   ir para o campo?

Melhorias gerais de arquitetura e as funções específicas das provas ficam de fora; elas já
estão no [checklist de requisitos](/requisitos-circ).

{{< notice "warning" >}}
**Respostas pendentes da equipe:** seis perguntas sobre hardware e decisões travam o
começo do trabalho. Respondam na issue
[#32](https://github.com/jmorais11-dev/rover_circ_ares/issues/32) (resumo na
[seção 6](#6-perguntas-para-a-equipe)).
{{< /notice >}}

## Resumo para toda a equipe

- **A simulação está pronta; o rover real, não.** O código compila do zero (CI do Docker
  verde), mas o caminho que liga os motores de verdade tem falhas de segurança.
- **O mais grave:** se o comando parar de chegar, ou se o programa for encerrado, **os
  motores continuam girando** com o último comando recebido. Nada no software os para.
- **Também bloqueia:** duas peças de hardware disputam a mesma porta USB, e o boot
  automático não é reproduzível.
- **A boa notícia:** os bloqueios de software são pequenos (dias, não semanas). O que
  falta para começar são **respostas de Elétrica e Embarcados** sobre o hardware.
- **Regra até lá:** motores só com **rodas suspensas** e com alguém na mão do **kill
  switch físico**.

### O que cada área precisa fazer

| Área | Pedido | Pergunta |
|---|---|---|
| Elétrica | Confirmar que o kill switch e os fusíveis existem e cortam a energia **dos servos** | 4 |
| Embarcados | Dizer qual controlador de motor e qual computador vão para a bancada | 1 |
| Embarcados / Telecom | Listar os sensores que existem fisicamente e como se ligam (serial, USB, ethernet) | 2 |
| Embarcados / Software | Aprovar o timeout do watchdog (proposta: 0,5 s) e testar o LX-16A sem comando | 5, 6 |
| Software | Decidir se o boot roda no host ou em Docker; depois, executar a [sequência](#5-sequência-de-ações) | 3 |

## 1. De onde vêm os requisitos

A base é o documento **Levantamento Inicial CIRC v2 (05/11/2026)**, que resume o
regulamento do CIRC 2027: [R3] regras, [R4] provas, [R5] segurança do rover. Ele é um
**resumo da equipe**, não o regulamento oficial; as páginas oficiais não foram
relidas nesta auditoria.

Itens marcados com **[I]** são **inferência nossa** (boa prática para um rover operado à
distância), não regra escrita.

**Legenda de status:**
**✅ Atendido** · **🟡 Parcial** · **❌ Ausente** · **❔ Não verificável** pelo
repositório (depende de hardware ou de documento externo).

## 2. Lançamento: ligar, inicializar e operar com segurança

| # | Requisito (fonte) | Status | Evidência |
|---|---|---|---|
| L1 | Kill switch físico, vermelho, iluminado, no topo, independente de computador [R5] | ❔ | É hardware. Nada no repositório confirma que existe. |
| L2 | Fusível ou disjuntor; proteção por software não vale [R5] | ❔ | É hardware. |
| L3 | 1 h só com bateria de bordo; bateria e BMS comerciais [R3][R5] | ❔ | Não há orçamento de energia ([#25](https://github.com/jmorais11-dev/rover_circ_ares/issues/25)). |
| L4 | Parar os motores quando o comando some (watchdog, perda de link) [R5 recomendado] | 🟡 | **Código pronto, falta bancada.** `controller_node` zera o duty se não chega comando por `cmd_timeout` (padrão 0,5 s) e repete o zero a cada 100 ms. |
| L5 | Parar os motores ao encerrar o programa (Ctrl+C, `systemctl stop`, falha) [I] | 🟡 | **Código pronto, falta bancada.** `controller_node_main.cpp` chama `shutdown()` (`kill_motors()`) depois do `spin`, no SIGINT e no SIGTERM. Um `kill -9` ou queda de energia ainda depende do watchdog do lado do hardware (kill switch). |
| L6 | Limitar os comandos de motor [I] | ✅ | `vel_parser_node.cpp` limita `linear.x` e `angular.z` nos dois sentidos; antes, `angular.z` negativo além do limite gerava raio de curva fora da faixa. O duty já era limitado a ±1000 no driver (`lx16a.cpp`, `set_motor_mode`). Teste: `test/test_vel_parser.cpp`. |
| L7 | Validar mensagens de motor [I] | ✅ | `controller_node` ignora `MotorsCommand` que não tenha 6 valores de tração e 4 de direção, e avisa no log. |
| L8 | Verificação automática na partida (montagem em 15 min) [R3] | 🟡 | `controller_node.cpp` confere se o device existe e tem permissão, e o nó agora falha se `connect()` não abrir a serial. Ainda ninguém verifica se os servos respondem. |
| L9 | Portas seriais estáveis [I] | ❌ | `urg_node_serial.yaml` e `ublox.yaml` usam **ambos** `/dev/ttyACM0`; servos em `/dev/ttyUSB0`. Sem regras udev, quem abre o quê depende da ordem em que o USB enumera. |
| L10 | Boot reproduzível (systemd) | 🟡 | `ros2/rover_service/` existe, mas: `After=network.service` em vez de `network-online.target`; sem `Restart=on-failure`; sem `ROS_DOMAIN_ID`. Assume ROS no host, contra o README (ROS só em Docker). `install.sh` usa caminhos relativos e instala 3 pacotes à mão em vez de `rosdep`. |
| L11 | Botão de habilitação no joystick (deadman) | 🟡 | `ps3.yaml`: `enable_button: 8` (L2); soltar o botão manda velocidade zero. Não protege se o joystick ou o nó cair no meio do comando (ver L4). |
| L12 | Modos desarmado / manual / autônomo [I] | ❌ | Não existe gerente de modos ([#18](https://github.com/jmorais11-dev/rover_circ_ares/issues/18)). Os motores aceitam comando assim que o nó sobe. |

## 3. Bancada: testar subsistemas sozinhos e juntos

| # | Requisito | Status | Evidência |
|---|---|---|---|
| B1 | Workspace compila a partir de máquina limpa | ✅ | `Dockerfile` e o workflow *Docker Build*, verde no `main`. |
| B2 | Testar a cinemática sem hardware | 🟡 | A simulação usa o mesmo `vel_parser_node` do rover real (`rover_gazebo/launch/include/cmd_vel.launch.py`). Mas o `controller_node` aborta se não houver serial: não há modo "sem hardware". |
| B3 | Testes automáticos do caminho até os motores | ❌ | O workflow *Tests* só roda para `tools/**` (política do MCP). Não há teste do `vel_parser` nem do protocolo LX-16A. |
| B4 | Drivers de sensores e TF do rover real | 🟡 | `rover.launch.py` sobe só `urg_node`, joystick e motores. Falta `robot_state_publisher` (sem TF `base_link→laser`), IMU e câmera. `ublox.launch.py` existe mas não é incluído, `ublox_gps` não está no `package.xml` e o `ublox.yaml` está em `tmode3: 1` (modo **estação base** RTK). |
| B5 | Telemetria de saúde: tensão e temperatura [R5 recomendado] | ❌ | O LX-16A já oferece leitura de temperatura e tensão (`SERVO_TEMP_READ`, `SERVO_VIN_READ` em `lx16a_consts.hpp`), mas nada é publicado. |
| B6 | Estação e rover separados por rede (operador não vê o rover) [R3] | ❌ | O joystick roda **no rover** (`joy_linux` em `rover.launch.py`). Não há launch da estação, IPs fixos nem `ROS_DOMAIN_ID` ([#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19)). |
| B7 | Calibração da direção e da geometria | 🟡 | `enc_min=250`, `enc_max=750` e `hardware_distances` são os valores do Sawppy original. Não há procedimento para medi-los no nosso chassi. |
| B8 | Gravação de dados (rosbag) | ❌ | [#20](https://github.com/jmorais11-dev/rover_circ_ares/issues/20). |
| B9 | Roteiro de bancada escrito | ❌ | No README, "Rover real" é um único comando. Não há passo a passo nem critério de aprovado/reprovado. |

## 4. Lacunas

### Bloqueantes

Impedem ligar o rover com segurança ou começar a bancada:

1. **L4 + L5:** o rover não para sozinho, nem quando o comando some nem quando o programa
   é encerrado. **Item mais grave.**
2. **L6 + L7:** comando sem limite e mensagem sem validação. Poucas linhas de correção;
   precisam estar prontas antes de alguém publicar comandos à mão.
3. **L9:** duas peças na mesma porta e nenhuma regra udev. O boot fica imprevisível.
4. **L10:** escolher e consertar um único caminho de boot (host ou Docker).
5. **L1 e L2:** confirmação de Elétrica de que kill switch e fusíveis existem e cortam a
   energia dos servos.
6. **B4 e B6:** bloqueiam a bancada **integrada** (sensores e estação), não a bancada só
   de motores.

### Importantes, mas não bloqueantes

L8 (verificação completa na partida), L12 (modos), B2 e B3 (modo sem hardware, testes no
CI), B5 (telemetria), B7 (calibração), B8 (rosbag), B9 (roteiro) e todos os itens de
prova do [checklist de requisitos](/requisitos-circ): GNSS, ArUco, UI do juiz, rádio,
braço, interfaces TRS.

## 5. Sequência de ações

A ordem segue as dependências: cada passo deixa o seguinte mais seguro ou possível.

{{< mermaid >}}
flowchart TD
  P1["1. Respostas da equipe<br/>issue #32"] --> P4["4. udev e portas"]
  P2["2. Segurança dos motores<br/>watchdog, parada, limites"] --> P3["3. Modo sem hardware<br/>e testes no CI"]
  P2 --> P6
  P4 --> P5["5. Boot único e<br/>verificação na partida"]
  P3 --> P6["6. Bancada de motores<br/>rodas suspensas"]
  P5 --> P6
  P6 --> P7["7. Rede estação ↔ rover<br/>teste de queda de link"]
  P7 --> P8["8. Sensores, TF, rosbag,<br/>telemetria, roteiro"]
{{< /mermaid >}}

1. **Responder às perguntas da [#32](https://github.com/jmorais11-dev/rover_circ_ares/issues/32).**
   Elas dizem quais portas, drivers e computador existem; todo o resto depende disso.
2. **Segurança dos motores** (L4–L7): timer que zera os motores sem comando novo por N ms;
   `kill_motors()` ao encerrar; validar o tamanho das mensagens; checar o `connect()`;
   limitar a velocidade dos dois lados e o duty a ±1000. Não depende de nada e reduz o
   risco de todo teste seguinte.
3. **Modo sem hardware e testes** (B2, B3): serial simulada ou opção `dry_run`, mais
   testes do `vel_parser` e do watchdog no CI. Valida o passo 2 sem ligar nada.
4. **Regras udev e portas por parâmetro** (L9). Vem antes do boot automático, que precisa
   de nomes estáveis.
5. **Boot único** (L10, L8 básico): um só caminho, serviço com `network-online.target`,
   `Restart=on-failure` e variáveis de ambiente; verificação na partida que conversa com
   cada servo e lê a tensão, com o resultado no log.
6. **Primeira bancada de motores**, rodas suspensas, kill switch confirmado: centralizar a
   direção, calibrar (B7) e cronometrar a parada ao matar o teleop.
7. **Rede estação ↔ rover** (B6): IPs fixos, `ROS_DOMAIN_ID`, joystick na estação e teste
   de queda de link (cabo desligado ou `tc netem`) para ver o watchdog agir.
8. **Sensores e TF** (B4) com o hardware que existir; depois rosbag (B8), telemetria
   (B5) e o roteiro de bancada escrito (B9).

## 6. Perguntas para a equipe

Respondam na issue [#32](https://github.com/jmorais11-dev/rover_circ_ares/issues/32),
citando o número da pergunta. Esta página será atualizada com as respostas.

| # | Pergunta | Quem responde | Resposta |
|---|---|---|---|
| 1 | O "rover menor remontado" usa servos LX-16A (o único hardware que o código suporta)? Qual é o computador de bordo e o sistema? | Embarcados, Estruturas | *pendente* |
| 2 | Quais sensores existem: Hokuyo serial ou ethernet? IMU (modelo)? A câmera Xtion do modelo é real? O u-blox é do rover ou é estação base RTK? | Embarcados, Telecom | *pendente* |
| 3 | O boot roda com ROS no host (como o `rover.service` assume) ou em Docker (como o README diz)? | Software | *pendente* |
| 4 | Kill switch e fusíveis já existem? O kill switch corta a energia dos servos? | Elétrica | *pendente* |
| 5 | Timeout do watchdog de 0,5 s está aceitável? | Software, Embarcados | *pendente* |
| 6 | Na bancada, com rodas suspensas: o LX-16A em modo motor mantém o último comando para sempre? | Bancada | *pendente* |

