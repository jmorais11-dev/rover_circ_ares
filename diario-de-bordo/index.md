# Diário de Bordo — Rover Sim


> Log técnico do desenvolvimento da simulação do rover: decisões, bugs encontrados e correções.


{{< toc >}}

Log técnico incremental. Cada entrada documenta o estado do projeto num dado
momento — o que foi decidido, o que quebrou e como foi corrigido. Ver também
os [Comandos Essenciais](/comandos-essenciais-simulacao) para rodar o que
está descrito aqui.

## 2026-11-19 — Segurança dos motores: o rover para sozinho quando algo dá errado

**Em uma frase:** antes, se o computador do rover perdesse o contato com quem
o comandava, as rodas continuavam girando para sempre. Agora elas param em
meio segundo.

### Como os motores recebem ordens

Pense numa cadeia de recados. Quem dirige (o joystick, o piloto automático
Nav2 ou a IA) diz "ande para frente a tal velocidade". Um programa traduz isso
em quanto cada uma das 6 rodas deve girar e para que ângulo cada uma das 4
rodas de direção deve virar. Um último programa, o `controller_node`, recebe
esses números e os manda pelo cabo serial para os servos LX-16A, que são os
motores. No ROS 2, cada um desses programas se chama **nó**, e os recados
viajam por canais com nome, os **tópicos**.

### O que estava errado

A [auditoria de prontidão](/auditoria-prontidao) apontou quatro problemas
nessa cadeia (itens L4 a L7):

1. **O último recado valia para sempre.** O servo só muda quando recebe uma
   ordem nova. Se o joystick desconectasse ou o Wi-Fi caísse, o rover seguia
   andando na última velocidade, sem ninguém no controle.
2. **Fechar o programa não parava as rodas.** Já existia uma função de
   "desligar motores", mas nada a chamava. Um Ctrl+C ou um desligamento do
   serviço deixava as rodas girando.
3. **Valores negativos não tinham limite.** Havia um teto para a velocidade
   positiva, mas não para a negativa. Uma curva fechada para um dos lados
   pedia um raio de curva fora da faixa que a direção aguenta.
4. **Recados malformados eram aceitos.** Uma mensagem com menos números do
   que o esperado (por exemplo, um comando digitado errado na bancada) fazia o
   programa ler memória que não devia.

Um quinto ponto ficou de bônus: se o cabo serial não abrisse, o programa
fingia que estava tudo certo.

### O que mudou

| Problema | Correção |
|---|---|
| Último recado valia para sempre | Um **watchdog** (cão de guarda) confere 10 vezes por segundo quando chegou o último comando. Se passou de 0,5 s, manda velocidade zero para as rodas e repete o zero até chegar comando novo. O tempo é configurável (`cmd_timeout`). |
| Fechar o programa não parava | Ao receber Ctrl+C ou `systemctl stop`, o programa zera as rodas e centraliza a direção antes de sair. |
| Valores negativos sem limite | Velocidade e giro agora têm limite nos dois sentidos. |
| Recados malformados | Mensagem sem exatamente 6 valores de tração e 4 de direção é ignorada, com aviso no log. |
| Serial que não abre | O programa para com erro claro, em vez de seguir rodando sem mandar nada. |

Junto com isso, a versão do `ros-mcp` (a ponte entre a IA e o ROS) foi fixada
em 3.1.2, que é a versão testada. Assim, uma atualização automática não muda
o comportamento sem a gente saber.

### Como foi testado, sem o rover

- **Teste automático:** um teste confere que uma ordem acima do limite, para
  frente ou para trás, produz o mesmo comando que o próprio limite. Os 17
  testes do pacote passaram.
- **Barramento falso:** um script cria uma porta serial de mentira e mostra o
  que cada servo receberia. Com ela:
  - as rodas foram para 500 e voltaram a 0 cerca de 0,5 s depois que os
    comandos pararam;
  - uma mensagem com tamanho errado foi recusada;
  - o Ctrl+C centralizou a direção e o programa saiu sem erro.

### O que ainda falta

- **Bancada com o rover real**, com as rodas suspensas e o kill switch à mão.
  É preciso confirmar que os servos de verdade obedecem e cronometrar a
  parada.
- **Casos que o software não cobre:** se o programa for morto à força
  (`kill -9`) ou faltar energia no computador, nenhum código roda. Aí quem
  protege é o kill switch físico.
- **Confirmar o 0,5 s com a equipe** (pergunta Q5 da
  [issue #32](https://github.com/Blazemorales/rover_circ_ares/issues/32)).
- **Colocar esse teste na CI**, para que uma mudança futura não desfaça a
  proteção sem ninguém perceber.

As mudanças estão na branch `fix/motor-safety-f0`.

## 2026-11-19 — Um só "volante": quem manda nas rodas e o botão de parada

**Em uma frase:** antes, vários programas davam ordens de velocidade ao
rover ao mesmo tempo, sem ninguém decidir quem tinha razão. Agora existe um
árbitro único, o joystick sempre ganha e um botão de parada por software
trava tudo.

### O problema

As ordens de velocidade chegam às rodas por um canal chamado `/cmd_vel`. É
como um volante que qualquer um pode pegar. Na simulação, **7 programas**
publicavam nele: o piloto automático (Nav2), cinco manobras dele (girar no
lugar, dar ré e outras) e até uma ponte do simulador que não servia para
nada. O joystick e o teclado também escreveriam ali. Quando dois falam ao
mesmo tempo, as rodas obedecem a quem falou por último.

Dois "filtros de segurança" do Nav2 também estavam fora do caminho:

- O **suavizador de velocidade** (`velocity_smoother`), que evita arrancadas
  e freadas bruscas, rodava, mas ninguém lia o que ele produzia.
- O **monitor de colisão** (`collision_monitor`), que freia o rover antes de
  bater num obstáculo visto pelo lidar, estava configurado mas nem era
  ligado.

### O que mudou

As ordens agora passam por uma fila fixa, e só um programa, o `twist_mux`,
pega o volante:

```
piloto automático ─► suavizador ─► monitor de colisão ─┐
joystick ───────────────────────────────────────────────┤ twist_mux ─► rodas
teclado ────────────────────────────────────────────────┘     ▲
                                                     botão /estop
```

- **Prioridade:** o joystick vence o teclado, que vence o piloto automático.
  Se o operador mexe no joystick, o rover obedece a ele na hora. Quando ele
  solta o joystick, o piloto volta a mandar meio segundo depois.
- **Parada de emergência por software (`/estop`):** uma mensagem `true`
  bloqueia todas as entradas, inclusive o joystick. O bloqueio fica até
  alguém mandar `false`; não se libera sozinho.
- **Freio de segurança:** se nenhuma ordem chega por meio segundo, o
  tradutor de velocidade (`vel_parser`) manda parar. Isso foi necessário
  porque o árbitro, quando bloqueia, simplesmente se cala em vez de mandar
  "zero", e o último comando continuaria valendo.

### O que os testes revelaram

Rodando na simulação, apareceram três problemas que a leitura do código não
mostrava:

1. **O `/estop` não parava o rover.** Três segundos depois de travar, as
   rodas simuladas ainda giravam. A causa era o silêncio do árbitro, descrito
   acima, e a correção foi o freio de meio segundo.
2. **O monitor de colisão estava no relógio errado.** A simulação tem um
   relógio próprio, e ele usava o do computador. Com isso, achava que todas
   as leituras do lidar eram de anos atrás, descartava todas e, por
   segurança, segurava o rover parado.
3. **O monitor de colisão procurava uma peça que não existe.** A
   configuração citava um ponto de referência chamado `base_footprint`, que o
   modelo deste rover não tem. O certo é `base_link`.
4. **O rover do simulador era maior do que o real.** No teste com uma caixa
   no caminho (feito em 23/11), o rover travava a uns 16 cm dela, mesmo com o
   monitor ainda deixando passar velocidade. Ele estava batendo: as peças que
   seguram as rodas de direção usavam como "casca de colisão" uma cópia da
   caixa do corpo inteiro (43 × 29 cm). Com isso, o rover simulado tinha 1 m
   de comprimento. A casca dessas peças agora é um cubo de 10 cm. Isso só
   afeta a simulação.
5. **O contorno usado pelo Nav2 era 4 cm curto.** As rodas vão até 34,3 cm à
   frente e atrás do centro, e o contorno (`footprint`) parava em 30 cm. Ele
   passou para 35 cm. Isso vale também para o rover real.

### Resultado na simulação

- O canal das rodas tem **um só** publicador (eram 7).
- O teclado move o rover, e o joystick passa por cima do teclado.
- O `/estop` zera as rodas em cerca de 0,3 s, e elas só voltam quando ele é
  liberado.
- Um objetivo de 2 m do piloto automático andou, parou no `/estop` e chegou
  ao destino depois de liberado.
- **Freio por obstáculo:** com uma caixa 2 m à frente e ordem de 0,3 m/s, o
  monitor de colisão reduziu a velocidade aos poucos (0,3 → 0,1 → 0,05 →
  0,025 m/s) e parou o rover com as rodas a cerca de 5 cm da caixa. Ele ficou
  parado até o fim do teste.

### O que ainda falta

- **Testar o joystick físico** no rover real.
- **Reconstruir a imagem Docker da equipe:** o `twist_mux` é um pacote novo.
- **Expor o `/estop` à IA e ao chat** (passo F3). Hoje ele só pode ser
  acionado de dentro do ROS.

As mudanças estão na branch `feat/cmd-vel-chain-f1`.

## 2026-11-16 — Pendências em aberto

Estado consolidado das pendências técnicas (antes no `to_continue.md`, que
saiu da raiz do repositório na reorganização).

**Navegação no terreno lunar:** melhorou de ~1/7 para 6/7 goals com o perfil
`uneven_terrain` (detalhes em [Chat Web](/chat-web)). Próximo passo: detectar
rampas íngremes de verdade com a câmera de profundidade (análise de
inclinação), já que o lidar 2D não distingue chão de parede.

**Chat web:** falta validar com Groq e Render reais. Já foi validado
localmente com o Ollama.

**Desempenho:** a meta de RTF ≥ 0,6 não foi atingida (0,42 com `sim_lite`).
O custo restante é fixo: física com passo de 1 ms (o `moon.world` não tem
bloco `<physics>`) e o gpu_lidar. A próxima ideia é testar `max_step_size`
0,002/0,004 com checagens de sanidade.

**Não bloqueantes:**
- O footprint em `ros2/rover_navigation/params/costmaps.yaml` é um placeholder
  de 0,6×0,6 m, não a medida real do chassi.
- A rolling window do `global_costmap` tem 30×30 m. Se o explore parecer
  "míope", aumente.
- Avisos ocasionais de "Control loop missed its desired rate" e "Message
  Filter dropping message" vêm de contenção de CPU. `headless:=true` e
  `sim_lite:=true` ajudam.

## 2026-11-11 — ROS-MCP e desempenho da simulação

**ROS-MCP:** o rover passou a aceitar comandos em linguagem natural via Model
Context Protocol. O LLM (qwen2.5:7b no Ollama) fala com um proxy restrito,
`rover_mcp_safe`, que fala com o `rosbridge` dentro do container. O LLM só
manda goals ao Nav2 e lê estado: `/cmd_vel` é bloqueado no proxy **e** no
próprio rosbridge. Validação: o LLM leu a odometria corretamente e uma
tentativa de publicar velocidade foi recusada; os goals mandados pelo LLM
abortaram com o `explore_lite` ativo e o modelo relatou sucesso — pendente.
Detalhes em [ROS-MCP](/ros-mcp).

**Desempenho:** a simulação rodava a RTF ~0,18. Um bisect mostrou que o
gargalo é a renderização da câmera RGBD, e que o custo é por quadro, não por
pixel. Novo perfil `sim_lite:=true` (320×240 @ 10 Hz, sem nuvem de pontos,
costmap local no lidar) leva o RTF a 0,42 sem quebrar a odometria visual.
Detalhes em [Desempenho da Simulação](/desempenho-simulacao).

## 2026-09-21 — Navegação autônoma (SLAM + exploração + Nav2): funcionando

**Objetivo:** o rover simulado explora sozinho (frontier exploration) e
navega com Nav2 evitando obstáculos, sem teleop e sem goals manuais.

**Resultado:** confirmado funcionando de ponta a ponta (headless e com GUI).
O rover se move sozinho via `explore_lite` + Nav2, o `/map` do
`slam_toolbox` cresce continuamente, e não aparecem mais avisos de "Robot is
out of bounds of the costmap".

### Decisão de escopo

O pacote `rover_nav2` mencionado em planos anteriores nunca chegou a existir
de fato. O repo upstream já trazia `rover_navigation` (SmacHybrid/SmacLattice
+ RPP/TEB) funcionando. A lacuna real era SLAM + exploração autônoma, então
foi criado um pacote novo, `rover_slam` (slam_toolbox + AMCL + explore_lite),
sem tocar em `rover_motor_controller_cpp/serial.cpp` e `.hpp` (edições locais
do usuário, propositalmente preservadas).

### O que foi feito

- Novo pacote `rover_slam/`:
  - `config/slam_toolbox.yaml`, `config/amcl.yaml`, `config/explore_params.yaml`
  - `launch/slam.launch.py` (slam_toolbox como lifecycle node, configure → activate)
  - `launch/amcl.launch.py` (map_server + amcl + lifecycle_manager_localization)
  - `launch/explore.launch.py` (explore_lite, do fork `robo-friends/m-explore-ros2`)
- `rover_gazebo/launch/gazebo.launch.py`:
  - argumentos novos: `slam` (default `True`), `explore` (default `True`), `map`,
    `headless` (default `False` — roda `gz sim -s`, sem GUI, útil para
    testes/CI sem gastar CPU em renderização)
  - trocou o include único de `rover_localization/launch/localization.launch.py`
    (que subia o `rtabmap` junto) por dois includes separados:
    `rgbd_odometry.launch.py` + `ekf.launch.py` (só odometria, sem SLAM visual)
  - inclui os launches do `rover_slam` condicionalmente
- `rover_gazebo/launch/moon.launch.py`: agora repassa `headless`, `slam`,
  `explore`, `launch_rviz` para `gazebo.launch.py` (antes ficavam presos aos
  defaults, sem poder sobrescrever via `ros2 launch ... slam:=False` etc.)

### Bugs encontrados e corrigidos

1. **Conflito de dono do `/map`.** `rtabmap` (SLAM visual, dentro do
   `localization.launch.py` original) competia com `slam_toolbox` pela
   transform `map → odom`. Corrigido subindo só `rgbd_odometry` + `ekf`
   (odometria), sem o `rtabmap` completo.
2. **`slam_toolbox` nunca ativava.** É um lifecycle node; o launch inicial
   usava um `Node` simples. Corrigido com `LifecycleNode` +
   `EmitEvent`/`RegisterEventHandler` (configure → activate), copiando o
   padrão do `online_async_launch.py` oficial do `slam_toolbox`.
3. **Processos zumbis entre testes.** `pkill -f` não matava tudo de forma
   confiável; sobravam `robot_state_publisher`/`joint_state_publisher`/bridges
   de execuções anteriores rodando junto com a atual, brigando pela tf.
   Forma segura de limpar, dentro do container:
   ```shell
   ps -eo pid=,comm= | awk '$1 != 1 {print $1}' | xargs -r kill
   ```
   **Nunca** usar `pkill -f` com padrões genéricos como `ros2`: casa com a
   própria linha de comando do `docker exec bash -c "..."` (que contém
   `/ros2_ws/`) e mata o processo errado — já aconteceu de derrubar o PID 1
   do container e precisar `docker start <container>` de novo.
4. **`/scan` com `frame_id` errado**, causa raiz do `slam_toolbox` descartar
   todo scan (mensagens "Message Filter dropping message... frame does not
   exist" / "timestamp earlier than transform cache"). O sensor lidar
   (`rover_description/urdf/sensors/hokuyo.urdf.xacro`) não tinha a tag
   `<gz_frame_id>`, então o Gazebo publicava `/scan` com
   `frame_id: rover/base_link/lidar` — uma frame que não existe na árvore de
   tf (o link real se chama `laser_link`). Corrigido adicionando
   `<gz_frame_id>${prefix}_link</gz_frame_id>` dentro do `<sensor>` do lidar,
   igual já era feito para o RGBD (`<optical_frame_id>camera_frame</optical_frame_id>`
   em `asus_xtion.urdf.xacro`).
5. **"Robot is out of bounds of the costmap" / "Robot out of costmap
   bounds"** no `explore_lite`. O `global_costmap` (em
   `rover_navigation/params/costmaps.yaml`) não tinha `rolling_window`,
   então seus limites vinham direto do `/map` do `slam_toolbox`. No início
   da exploração, a área embaixo/atrás do robô ainda não tinha sido varrida
   pelo lidar (ponto cego atrás do sensor), então o `/map` nascia sem cobrir
   a pose do robô — e como o `explore_lite` também lê
   `/global_costmap/costmap`, isso travava os dois num deadlock: sem costmap
   válido não navega, sem navegar o mapa não cresce. Corrigido adicionando
   `rolling_window: true`, `width: 30`, `height: 30` ao `global_costmap` —
   ele passa a ficar sempre centrado no robô, independente de onde o `/map`
   do SLAM já cresceu.
6. **Gazebo GUI travava** com "Authorization required, but no authorization
   protocol specified" / "could not connect to display :0", e o launch
   matava o `gz sim server` inteiro junto com a GUI. Faltava autorização X11
   do host para o container. Corrigido no host com `xhost +local:docker`
   (não persiste entre reboots — repetir se voltar a acontecer). Para testes
   automatizados/CI, usar `headless:=True` em vez de depender de X11.
7. **Robô nunca se movia fisicamente**, mesmo publicando `/cmd_vel`
   manualmente e mesmo com Nav2 enviando goals — causa raiz de tudo "falhar
   em progredir" e do `explore_lite` esgotar frontiers rapidamente sem o
   robô sair do lugar. O pacote `ros2controlcli` (fornece o verbo
   `ros2 control`, usado por `rover_gazebo/launch/include/spawn.launch.py`
   para ativar `joint_state_broadcaster`/`position_controller`/
   `velocity_controller` via `ros2 control load_controller --set-state
   active ...`) não estava instalado na imagem/container. Os processos de
   spawn morriam na hora com `invalid choice: 'control'` (exit code 2), e
   `ros2 service call /controller_manager/list_controllers ...` confirmava
   zero controllers ativos. Corrigido:
   - instalado `ros-jazzy-ros2controlcli` no container (não persiste se a
     imagem for reconstruída do zero)
   - adicionado `<depend>ros2controlcli</depend>` em
     `rover_gazebo/package.xml`, para que `rosdep install --from-paths src
     --ignore-src -r -y` (chamado no `Dockerfile` da raiz do repo) instale
     isso automaticamente em builds futuros da imagem.

### Status confirmado

Testado tanto com `headless:=True` quanto com a GUI normal do Gazebo (depois
do `xhost +local:docker`):

- `/scan` publica de verdade, com `frame_id: laser_link` correto.
- `map → base_link` resolve e atualiza continuamente.
- `/map` cresce sem parar enquanto o robô explora (visto crescendo de 90x62
  para 173x193+ células em ~1 min de exploração).
- Zero ocorrências de "Robot is out of bounds of the costmap" ou
  "[FrontierSearch] Robot out of costmap bounds".
- `explore_lite` conecta no Nav2, manda goals sozinho, e não para cedo com
  "All frontiers traversed/tried out" (isso só acontecia antes porque o robô
  ficava fisicamente parado — bug #7).
- Robô se desloca de verdade (odom saindo de `(0,0)` e progredindo, ex.:
  `(0.33, 2.10) → (1.72, 3.33)` em ~1 min), sem teleop nem goal manual.
- `ros2 service call /controller_manager/list_controllers ...` mostra os 3
  controllers (`joint_state_broadcaster`, `position_controller`,
  `velocity_controller`) com `state='active'`.

### Pendências conhecidas (não bloqueantes)

- Footprint em `rover_navigation/params/costmaps.yaml` é placeholder
  0.6x0.6m, não é a medida real do chassi Sawppy — ajustar só se o
  comportamento de desvio de obstáculo parecer errado na prática.
- `width`/`height: 30` (metros) do `global_costmap` rolling window é um
  chute razoável para o tamanho do `moon.world` (~100x100m de terreno) — se
  o `explore_lite` parecer "míope" (só olhando frontiers muito perto),
  considerar aumentar.
- Ainda aparecem alguns "Message Filter dropping message... timestamp
  earlier than transform cache" ocasionais e "Control loop missed its
  desired rate" no `controller_server` — sintoma de contenção de CPU
  (Gazebo + Nav2 + SLAM juntos). Não impede o progresso, mas
  `headless:=True` ajuda bastante.
- Se a imagem Docker for reconstruída do zero, o `ros2controlcli` já vem
  incluído via `rosdep install` (fix do bug #7 no `package.xml`) — não
  precisa mais instalar manualmente.

### Como retomar

Repositório montado dentro do container em `/workspaces/ros2_ws` (mesmo
diretório do host). Não instalar ROS 2/colcon no host — tudo roda dentro do
container, de propósito. Comandos completos em
[Comandos Essenciais](/comandos-essenciais-simulacao).

Para GUI: `xhost +local:docker` no host antes de abrir o container (não
persiste entre reboots). Para rodar sem GUI (CI/testes rápidos):
`headless:=True`.

```shell
ros2 launch rover_gazebo moon.launch.py slam:=True explore:=True headless:=True
```

## 2026-09-22 — `explore_lite` nunca estava de fato no workspace: achado e corrigido

**Objetivo:** validar ao vivo, rodando de verdade dentro do `rover_dev`, que
o `slam:=True explore:=True` da entrada anterior funciona ponta a ponta.

**Resultado:** não funcionava.
`ros2 launch rover_gazebo moon.launch.py slam:=True explore:=True headless:=True`
morria logo no início com `package 'explore_lite' not found`, derrubando
(cascade shutdown) tudo que já tinha subido.

### Causa raiz

`rover_slam/package.xml` declara `<depend>explore_lite</depend>`, mas
`explore_lite` é um fork (`robo-friends/m-explore-ros2`, pacote na subpasta
`explore/`, mais uma dependência dele, `explore_lite_msgs`) que não é uma
chave resolvível pelo `rosdep`. O `Dockerfile` roda
`rosdep install --from-paths src --ignore-src -r -y` — a flag `-r` faz o
`rosdep` **pular em silêncio** dependências que falham em resolver, então o
pacote nunca chegou a existir de fato no workspace, apesar do `package.xml`
parecer completo e do build do Docker terminar sem erro visível.

**Correção:** vendorizados `explore_lite/` e `explore_lite_msgs/` (do fork
acima; `map_merge/`, que não é usado aqui, ficou de fora) como pastas de
pacote no nível raiz do repo, no mesmo padrão flat de `rover_slam`/
`rover_navigation`. Assim o `colcon build` resolve por nome de pacote
dentro do próprio workspace, sem depender do `rosdep` pra isso.

### Bug batido no caminho: processos `gz sim` órfãos

Durante os testes, ficou mais de uma instância de `gz sim` rodando ao mesmo
tempo — o wrapper do `ros2 launch` morre no shutdown (ou quando a sessão do
`docker exec` que o iniciou fecha), mas o processo `gz sim` de baixo escapa
e fica órfão, reparented pro PID 1, continuando a rodar. Sintoma:
`slam_toolbox` soltando "Message Filter dropping message... timestamp
earlier than transform cache" sem parar, com o `/clock` pulando pra frente
e pra trás — duas simulações concorrentes disputando o tempo. Resolvido
listando `ps -ef | grep "gz sim"` e matando por PID exato (repetindo o
aviso já dado acima sobre `pkill -f`: `pkill -f "gz sim"`/`pkill -f "ros2"`
também casa com a própria linha de comando do `docker exec`/`pgrep` usada
pra limpar, e pode matar o processo errado).

### Confirmado funcionando (depois da correção)

- `map` resolve e `map` → `base_link` progride sozinho.
- Os 3 controllers (`joint_state_broadcaster`, `position_controller`,
  `velocity_controller`) ficam `active`.
- `/map` cresceu de 96x80 para 106x83 células em ~40s de exploração.
- Robô andou sozinho de `(0.68, 0.51)` para `(0.79, 1.03)` (tempo de sim
  4.5s → 9.9s), sem teleop nem goal manual.
- Zero ocorrência de "Robot is out bounds costmap" ou crash.

