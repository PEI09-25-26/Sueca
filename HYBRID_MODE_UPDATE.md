# Hybrid Mode - Update Rapido

## O que foi adicionado agora

- Suporte para **1 a 3 jogadores virtuais** por sala.
- Escolha de papel no lobby hibrido para nao-host:
  - `jogador real`
  - `jogador virtual`
- Fluxo de distribuicao real por visao:
  - Host mostra cartas na camera.
  - Backend reconhece e distribui para o virtual correto, 10 cartas por virtual.
- Fluxo de jogadas durante a partida:
  - Virtual escolhe carta na app.
  - Host ve essa carta para jogar fisicamente na mesa.
  - Quando a camera confirma a captura, backend executa a jogada e remove a carta da mao virtual.
  - Para jogadores reais, host tambem confirma jogada por captura da carta na mesa.

## Backend (sueca_1.3)

### Novo ficheiro
- `sueca_1.3/hybrid_game_coordinator.py`
  - Estado hibrido por sala (`game_id`)
  - papeis por jogador (`real`/`virtual`)
  - ordem e maos dos virtuais
  - carta virtual pendente para o host confirmar

### Ficheiros alterados
- `sueca_1.3/hybrid_vision_service.py`
  - novo metodo `recognize_once(frame_base64)`
- `sueca_1.3/server.py`
  - novo metodo `play_card_hybrid_capture(...)` na `GameState`
  - novas rotas:
    - `POST /api/hybrid/register_player`
    - `GET /api/hybrid/state`
    - `POST /api/hybrid/deal/reset`
    - `POST /api/hybrid/deal/recognize`
    - `POST /api/hybrid/virtual/select_card`
    - `GET /api/hybrid/pending_play`
    - `POST /api/hybrid/play/confirm_capture`

## Frontend (frontend_REST)

### Ficheiros alterados
- `frontend_REST/app/app/src/main/res/layout/activity_room_hybrid.xml`
  - switch para escolher papel virtual/real
- `frontend_REST/app/app/src/main/java/com/example/MVP/RoomHybridActivity.kt`
  - passa `isVirtualPlayer` para o jogo
- `frontend_REST/app/app/src/main/java/com/example/MVP/HybridActivity.kt`
  - regista papel no backend
  - host faz captura/distribuicao para multiplos virtuais
  - virtual recebe cartas em tempo real
  - virtual escolhe carta e host confirma por captura
- `frontend_REST/app/app/src/main/java/com/example/MVP/models/Models.kt`
  - novos modelos de runtime hibrido
- `frontend_REST/app/app/src/main/java/com/example/MVP/network/ApiService.kt`
  - novos endpoints hibridos

## Nota curta

- O jogo normal continua inalterado.
- O modo hibrido usa rotas dedicadas (`/api/hybrid/*`) para nao quebrar o fluxo online existente.
- Se aparecer aviso de `cv2`/`flask_cors` no editor, instala deps com:
  - `pip install -r sueca_1.3/requirements.txt`
