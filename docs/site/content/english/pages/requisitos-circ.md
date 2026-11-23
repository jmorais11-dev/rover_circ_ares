---
title: "Requisitos do CIRC — Checklist"
meta_title: "Requisitos do CIRC"
description: "Requisitos do regulamento e das provas do CIRC 2027 e o que falta no projeto, em forma de checklist."
draft: false
---

{{< toc >}}


Base: regulamento e provas do CIRC 2027 ([R3] regras, [R4] provas, [R5] segurança), usados como
especificação para competir em 2028. Fonte: *Levantamento Inicial CIRC v2 (05/11/2026)*.

Os números `#` são as issues do repositório `jmorais11-dev/rover_circ_ares`. A [#26](https://github.com/jmorais11-dev/rover_circ_ares/issues/26) acompanha todas.

## 1. Requisitos gerais do rover [R3]

| Requisito | Valor |
|---|---|
| Massa | Abaixo de 50 kg (±1% de pontos por kg). Acima de 70 kg o rover não opera. |
| Energia | Pelo menos 1 h só com bateria de bordo. Cabo de alimentação é proibido. |
| Montagem | 15 min para montar e 10 min para desmontar. |
| Ambiente | Chuva, lama, vento, escuridão e 40 °C do lado de fora. |
| Manipulação | Objetos de até 5 kg e 90 mm de largura (garra abrindo até 100 mm). |
| Tamanho | Passar por uma porta de 0,8 m. |
| Autoria | Projeto da equipe. Pode usar bibliotecas abertas e controladores de motor comprados. |

- [ ] Fechar o orçamento de massa e de energia do computador de bordo e dos sensores, junto com Elétrica e Estruturas ([#25](https://github.com/jmorais11-dev/rover_circ_ares/issues/25))
- [ ] Self-check automático na inicialização para caber nos 15 min ([#18](https://github.com/jmorais11-dev/rover_circ_ares/issues/18))
- [ ] Monitorar temperatura e cortar acima do limite ([#18](https://github.com/jmorais11-dev/rover_circ_ares/issues/18))

## 2. Segurança [R5]

**Fora do software (obrigatório):**

- [ ] Kill switch físico, vermelho, iluminado e no topo, que corte toda a energia sem depender de computador
- [ ] Nenhum outro botão vermelho no rover
- [ ] Fusíveis ou disjuntores. Proteção só por software não vale.
- [ ] Limites mecânicos nas juntas do braço. Limite por software não é mais aceito.
- [ ] Bateria comercial com BMS comercial. LiFePO4 tem desconto de 40% no peso. Menos de 1000 Wh, fácil de remover.
- [ ] Recomendado: parada remota por um rádio independente do link principal

**Software ([#18](https://github.com/jmorais11-dev/rover_circ_ares/issues/18)):**

- [ ] Gerente de modos (desarmado, manual, autônomo)
- [ ] Watchdog no `/cmd_vel` e heartbeat da estação, com parada se o link cair
- [ ] Telemetria de bateria, corrente e temperatura
- [ ] Limites de velocidade por modo

## 3. Comunicação [R3]

| Requisito | Valor |
|---|---|
| Link | Sempre sem fio, sem celular nem satélite, dentro das regras da ISED |
| Canais proibidos | 5 GHz: 140, 144, 149, 153, 157, 161 e 165 |
| Antena | Mastro de até 4 m. Se for orientável, gira só por motor ou controle remoto. |
| Backhaul | Ethernet 100BASE-TX, MTU 1500, sem DHCP, 50–100 Mbit/s |
| Capacidade mínima | Dirigir, manipular e receber telemetria, mesmo sem vídeo |

- [ ] Escolher o rádio e os canais junto com Telecom ([#25](https://github.com/jmorais11-dev/rover_circ_ares/issues/25))
- [ ] IPs fixos, sem DHCP ([#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19))
- [ ] Comando e telemetria com prioridade sobre o vídeo ([#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19))
- [ ] Vídeo adaptativo com GStreamer em H.265 e troca de câmera ([#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19))
- [ ] Monitor de link e testes com perda e atraso simulados por `tc netem` ([#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19))
- [ ] Avaliar Zenoh contra DDS ([#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19))

## 4. Autonomia [R3][R4]

| Requisito | Valor |
|---|---|
| Definição | Nenhuma entrada do operador. Qualquer toque nos controles anula a autonomia. |
| Waypoints | GNSS, WGS 84, graus decimais |
| Rumo | Norte geográfico = 0°, com a declinação de Drumheller |
| Distâncias | Medidas pelo odômetro sobre o terreno |
| ArUco | Dicionário 4x4_100, leitura mostrada automaticamente ao juiz |

- [ ] GNSS na simulação, `navsat_transform` e EKF fundindo GNSS, IMU e odometria de rodas ([#11](https://github.com/jmorais11-dev/rover_circ_ares/issues/11))
- [ ] Rumo absoluto com correção de declinação ([#12](https://github.com/jmorais11-dev/rover_circ_ares/issues/12))
- [ ] Indicador de entrada e saída do modo autônomo ([#15](https://github.com/jmorais11-dev/rover_circ_ares/issues/15))
- [ ] Detecção ArUco com tela para o juiz ([#16](https://github.com/jmorais11-dev/rover_circ_ares/issues/16))

## 5. Provas de 2027 [R4]

### Automated Demolition and Clearing (inteiramente autônoma)

- [ ] Actions de movimento: `Drive Forward` e `Drive Backwards` (1/3/5 m), `Rotate`, `Rotate and Drive` ([#14](https://github.com/jmorais11-dev/rover_circ_ares/issues/14))
- [ ] `Face Bearing`, `Report Bearing`, `Report GNSS`, `Drive to Waypoint` (até 3 m), `Drive to Marked Waypoint` (até 1 m) ([#14](https://github.com/jmorais11-dev/rover_circ_ares/issues/14))
- [ ] `Read and Store Markers` e `Retrieve Markers` ([#16](https://github.com/jmorais11-dev/rover_circ_ares/issues/16))
- [ ] Comandos EFF do braço ([#23](https://github.com/jmorais11-dev/rover_circ_ares/issues/23))
- [ ] UI do juiz com botões `[short] long name`, campos com unidade e disparo com um clique ([#15](https://github.com/jmorais11-dev/rover_circ_ares/issues/15))

### Meteorite Search (sem GPS)

- [ ] Navegação por odometria de rodas e IMU, relativa a marcos ([#13](https://github.com/jmorais11-dev/rover_circ_ares/issues/13))
- [ ] Fotos de dois ângulos (≥ 90° entre elas) e panorama de 180°/360° ([#17](https://github.com/jmorais11-dev/rover_circ_ares/issues/17))
- [ ] Leitura do contador Geiger por TRS ([#22](https://github.com/jmorais11-dev/rover_circ_ares/issues/22))
- [ ] Relatório entregue até 2 h depois da prova ([#20](https://github.com/jmorais11-dev/rover_circ_ares/issues/20))

### Reactor Recovery

- [ ] Setores com tempestade em horário marcado, via keepout do Nav2 variando no tempo ([#21](https://github.com/jmorais11-dev/rover_circ_ares/issues/21))
- [ ] Receptor de beacon por UART/TRS ([#22](https://github.com/jmorais11-dev/rover_circ_ares/issues/22))
- [ ] Pegar objetos de até 5 kg com ponto de pega de até 80 mm ([#23](https://github.com/jmorais11-dev/rover_circ_ares/issues/23))

### Prison Break (à noite)

- [ ] Terminal serial do console de segurança por TRS ([#22](https://github.com/jmorais11-dev/rover_circ_ares/issues/22))
- [ ] Câmeras para pouca luz, sem iluminar o chão, nem com infravermelho (hardware e [#24](https://github.com/jmorais11-dev/rover_circ_ares/issues/24))

### Mining Site Remote Operations

- [ ] Operação inteira pelo backhaul, dentro do limite de banda ([#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19))
- [ ] Opcional: usar a nuvem de pontos LIDAR de 2018 no planejamento ([#24](https://github.com/jmorais11-dev/rover_circ_ares/issues/24))

## 6. Braço [R3][R4] ([#23](https://github.com/jmorais11-dev/rover_circ_ares/issues/23))

- [ ] Braço e garra no URDF, com ros2_control
- [ ] MoveIt 2 e MoveIt Servo
- [ ] Câmera na garra para aproximação guiada por ArUco
- [ ] Marca de referência na ponta e relatório de x/y/z relativo ao pacote indicador

## 7. Infraestrutura e testes

- [ ] Mundo de simulação com ArUco, torres, objetos e cenário noturno ([#24](https://github.com/jmorais11-dev/rover_circ_ares/issues/24))
- [ ] Gravação com `ros2 bag` e log de missão ([#20](https://github.com/jmorais11-dev/rover_circ_ares/issues/20))
- [ ] Documento de interfaces com Embarcados, Elétrica, Telecom e Estruturas ([#25](https://github.com/jmorais11-dev/rover_circ_ares/issues/25))

## Já atendido

- [x] ROS 2 Jazzy com Nav2, rtabmap e slam_toolbox
- [x] Simulação em Gazebo com ros2_control
- [x] Teleoperação por joystick e teclado
- [x] CI e imagem Docker (o workspace compila de uma máquina limpa)
- [x] Navegação em terreno irregular e missões em sequência (`run_mission`)

## Parcialmente atendido

- [ ] Implantação via systemd: o serviço existe, mas o boot ainda não é reproduzível (ver [auditoria de prontidão](/auditoria-prontidao), item L10, e [#32](https://github.com/jmorais11-dev/rover_circ_ares/issues/32))

## Ordem sugerida

A segurança vem primeiro: sem ela não dá para ligar o rover real nem fazer bancada. Detalhes na [auditoria de prontidão](/auditoria-prontidao).

1. [#32](https://github.com/jmorais11-dev/rover_circ_ares/issues/32) e [#18](https://github.com/jmorais11-dev/rover_circ_ares/issues/18): respostas da equipe sobre o hardware e segurança dos motores (watchdog, parada ao encerrar, limites), antes de qualquer teste em hardware real
2. [#19](https://github.com/jmorais11-dev/rover_circ_ares/issues/19): rede entre estação e rover, com teste de queda de link
3. [#11](https://github.com/jmorais11-dev/rover_circ_ares/issues/11), [#12](https://github.com/jmorais11-dev/rover_circ_ares/issues/12) e [#14](https://github.com/jmorais11-dev/rover_circ_ares/issues/14): GNSS, rumo e actions de movimento
4. [#16](https://github.com/jmorais11-dev/rover_circ_ares/issues/16) e [#15](https://github.com/jmorais11-dev/rover_circ_ares/issues/15): ArUco e UI do juiz. Com isso a prova de demolição já pode ser treinada inteira na simulação.
5. [#13](https://github.com/jmorais11-dev/rover_circ_ares/issues/13), [#17](https://github.com/jmorais11-dev/rover_circ_ares/issues/17), [#20](https://github.com/jmorais11-dev/rover_circ_ares/issues/20) a [#22](https://github.com/jmorais11-dev/rover_circ_ares/issues/22) e [#24](https://github.com/jmorais11-dev/rover_circ_ares/issues/24): as outras provas
6. [#23](https://github.com/jmorais11-dev/rover_circ_ares/issues/23): braço, no 1º semestre de 2028
