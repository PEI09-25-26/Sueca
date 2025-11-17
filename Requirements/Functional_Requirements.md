✅ Requisitos Funcionais

1. Gestão de Conta e Perfil

RF1.1 – Registo e Autenticação
O sistema deve permitir ao utilizador criar conta e fazer login.

RF1.2 – Alterar Nome de Utilizador
O sistema deve permitir ao utilizador alterar o seu nome de utilizador através do menu de perfil.

RF1.3 – Alterar Foto de Perfil
O sistema deve permitir ao utilizador alterar a sua fotografia de perfil.

RF1.4 – Consultar Histórico de Partidas
O sistema deve permitir ao utilizador visualizar estatísticas pessoais: número de jogos, vitórias, win rate e melhor pontuação.

⸻

2. Gestão de Lobbies e Tabelas Online

RF2.1 – Criar Mesa Online
O sistema deve permitir criar uma mesa online para jogar Sueca.

RF2.2 – Entrar numa Mesa Online
O sistema deve permitir entrar numa mesa online existente.

RF2.3 – Iniciar Partida Online
O sistema deve permitir ao anfitrião iniciar a partida após a mesa estar pronta.

RF2.4 – Jogar Sueca Online
O sistema deve permitir jogar Sueca online com todas as regras e progressão normal do jogo.

RF2.5 – Atribuir Jogadores a Equipas
O sistema deve permitir associar jogadores (humanos ou IA) a equipa A ou B ao configurar uma partida.

RF2.6 - Trocar de lugar na mesa
O sistema deve permitir trocar de lugar na mesa antes da partida começar

⸻

3. Suporte a Partidas Físicas

RF3.1 – Criar Mesa Física
O sistema deve permitir criar uma sessão de Sueca física com detecção de cartas e arbitragem.

RF3.2 – Sincronizar Estado da Mesa Física
O sistema deve sincronizar o estado do jogo físico em tempo real com utilizadores remotos.

RF3.3 – Participar Remotamente em Mesa Física
O sistema deve permitir que um utilizador remoto jogue numa mesa física, vendo o estado da mesa e escolhendo cartas.

RF3.4 - Comunicar com os Jogadores a partir de Áudio
O sistema deve de comunicar com filas de áudio quando algumas situações acontecem (ex.: batota, jogar cartas, etc.)

⸻

4. Integração com IA em Jogos

RF4.1 – Adicionar Jogadores IA em Jogos Físicos
O sistema deve permitir adicionar jogadores controlados por IA a uma partida física.

RF4.2 – Adicionar Jogadores IA em Jogos Online
O sistema deve permitir adicionar jogadores IA em mesas online.

RF4.3 – Ajustar Nível de Dificuldade da IA
O sistema deve permitir selecionar o nível de perícia da IA (ex.: fácil, médio, difícil).

RF4.4 – Decisão da IA
A IA deve ser capaz de tomar decisões e jogar cartas conforme as regras oficiais de Sueca.

⸻

5. Detecção de Cartas e Processamento de Imagem

RF5.1 – Detetar Cartas com Câmara
O sistema deve detetar automaticamente na imagem as cartas mostradas (naipe e valor).

RF5.2 – Detetar Cartas na Mesa
O sistema deve identificar cartas jogadas na mesa durante uma ronda.

⸻

6. Arbitragem Automática e Regras

RF6.1 – Validar Jogada
O sistema deve validar automaticamente se a carta jogada é legal conforme as regras de Sueca.

RF6.2 – Rejeitar Jogada Ilegal
O sistema deve impedir a jogada e informar o utilizador em caso de violação das regras.

RF6.3 – Determinar Vencedor da Vaza
O sistema deve identificar automaticamente o vencedor da vaza quando as quatro cartas forem jogadas.

RF6.4 – Atualizar Ordem de Jogo
O sistema deve atualizar a ordem de jogo dinamicamente após cada vaza.

⸻

7. Torneios

RF7.1 – Criar Torneio
O sistema deve permitir a criação de torneios com configuração de regras e tipo de bracket.

RF7.2 – Entrar em Torneio
O sistema deve permitir ao utilizador entrar em torneios ativos.

RF7.3 – Preencher Bracket com IA
O sistema deve permitir ao organizador preencher vagas vazias com jogadores IA.

RF7.4 – Atualização em Tempo Real do Torneio
O sistema deve atualizar automaticamente resultados, progressão e scores nas chaves do torneio.

RF7.5 – Gerar Bracket e Avançar Vencedores
O sistema deve gerir automaticamente as rondas e avançar vencedores no bracket.

⸻

8. Sincronização e Comunicação em Tempo Real

RF8.1 – Sincronização de Estado da Mesa Online
O sistema deve atualizar jogadas, pontuações e estado da mesa para todos os jogadores online em tempo real.

RF8.2 – Sincronização da Mesa Física para Jogadores Remotos
O sistema deve transmitir a deteção de cartas e o estado do jogo físico para utilizadores remotos imediatamente.

RF8.3 – Identificar Cartas do Jogador Remoto
O sistema deve identificar as cartas de um jogador remoto através da câmara ou input manual.

RF8.4 - Atualizar o Histórico
O sistema deve atualizar o histórico do user depois de um jogo

⸻

9. Modo de Exibição Pública

RF9.1 – Ativar Modo de Exibição Pública
O sistema deve permitir ativar um modo de ecrã público sem interação.

RF9.2 – Mostrar Estado do Jogo
O sistema deve exibir estado do jogo, próxima jogada e pontuação num layout visual acessível.

RF9.3 – Mostrar Estado do Torneio
O sistema deve exibir brackets e scores de torneios em tempo real.

⸻
