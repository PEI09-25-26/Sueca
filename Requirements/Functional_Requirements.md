# Requisitos Funcionais

## 1. Reconhecimento Automático de Cartas

- **Descrição:** A aplicação deve ser capaz de reconhecer automaticamente as cartas apresentadas à câmara, mesmo quando estas estiverem parcialmente sobrepostas ou inclinadas, garantindo uma identificação precisa e consistente durante toda a partida.
- **Como é cumprido:** O sistema utiliza algoritmos de visão computacional (OpenCV) aliados a modelos de deteção profunda (YOLO), previamente treinados com imagens variadas, incluindo diferentes ângulos e sobreposições.
- **Suposições:** As cartas estão legíveis no campo de visão da câmara e o ambiente apresenta uma iluminação razoável.
  
## 2. Processamento do Estado do Jogo e Estratégia

- **Descrição:** Deve processar a informação do estado do jogo adquirida pelas cartas reconhecidas e pelo comportamento dos jogadores, para calcular a jogada mais adequada, tendo em conta as regras oficiais da Sueca e a estratégia mais vantajosa possível.
- **Como é cumprido:** Um módulo implementa o motor de lógica e estratégia, considerando o histórico das jogadas e aplicando as regras pré-definidas.
- **Suposições:** As regras da Sueca não são alteradas durante a execução do jogo.
  
## 3. Comunicação Eficaz das Jogadas

- **Descrição:** A aplicação deve comunicar rapidamente ao jogador humano a carta que deve ser jogada, utilizando recursos de áudio claros e não intrusivos, permitindo que o jogador execute a jogada sem confusão ou atraso.
- **Como é cumprido:** Integração de síntese de voz nativa na aplicação para comunicar decisões de jogada, com instruções simples e objetivas.
- **Suposições:** O dispositivo possui colunas ou acesso a auscultadores para o jogador ouvir a instrução.
  
## 4. Registo e Atualização de Pontuação

- **Descrição:** O sistema deve registar a pontuação individual de cada jogador e a pontuação consolidada das equipas, atualizando essa informação em tempo real para que todos os jogadores tenham conhecimento do estado do jogo.
- **Como é cumprido:** O sistema mantém um registo dinâmico de pontuação, apresentado visualmente na interface a cada rodada.
- **Suposições:** Não há falhas críticas na aplicação que possam interromper o registo.
  
## 5. Deteção de Erros e Jogadas Inválidas

- **Descrição:** Deve implementar mecanismos para detetar erros ou jogadas inválidas, como renúncias (quando um jogador não tem carta da cor pedida), e alertar os jogadores para que estas situações sejam corrigidas conforme as regras.
- **Como é cumprido:** O motor de jogo valida as ações dos jogadores em cada jogada e gera alertas em caso de incumprimento das regras.
- **Suposições:** Os dados das cartas jogadas são reconhecidos corretamente.
  
## 6. Armazenamento de Estatísticas de Desempenho

- **Descrição:** Deve armazenar estatísticas do desempenho do jogo, incluindo frequência de jogadas, cartas jogadas por cada jogador, e resultados das partidas, permitindo posteriormente a análise e avaliação dos jogadores.
- **Como é cumprido:** Implementação de um módulo de armazenamento local para registo de eventos e resultados do jogo.
- **Suposições:** O utilizador não apaga manualmente os dados entre sessões.
  
## 7. Organização e Gestão de Torneios

- **Descrição:** A aplicação deve permitir a organização e gestão de torneios, possibilitando o registo de múltiplas partidas, classificação de jogadores e equipas, e acompanhamento do progresso dos torneios.
- **Como é cumprido:** Módulo de torneios que gera tabelas, calendários e rankings automaticamente com base nos resultados das partidas.
- **Suposições:** O utilizador segue o fluxo de utilização para criar e gerir torneios conforme o manual da aplicação.
  
## 8. Configuração Personalizada de Regras

- **Descrição:** Deve permitir a configuração personalizada das regras e modos de jogo, para acomodar variantes regionais da Sueca ou preferências dos jogadores.
- **Como é cumprido:** Interface de configuração acessível que permite selecionar opções e variantes compatíveis.
- **Suposições:** O utilizador compreende as opções disponíveis e escolhe regras suportadas pelo sistema.
  
## 9. Feedback Visual e Auditivo Intuitivo

- **Descrição:** Deve assegurar que todas as interações do sistema com o utilizador sejam intuitivas, fornecendo feedback visual e auditivo durante o jogo para informar sobre o estado atual, jogadas possíveis e ações necessárias.
- **Como é cumprido:** Utilização de alertas, feedback sonoro, destaques visuais e mensagens claras na interface.
- **Suposições:** O utilizador está atento aos avisos apresentados pela aplicação.
- **Descrição:** Deve permitir a configuração personalizada das regras e modos de jogo, para acomodar variantes regionais da Sueca ou preferências dos jogadores.
- **Como é cumprido:** Interface de configuração acessível que permite selecionar opções e variantes compatíveis.
- **Suposições:** O utilizador compreende as opções disponíveis e escolhe regras suportadas pelo sistema.

## 9. Feedback Visual e Auditivo Intuitivo

- **Descrição:** Deve assegurar que todas as interações do sistema com o utilizador sejam intuitivas, fornecendo feedback visual e auditivo durante o jogo para informar sobre o estado atual, jogadas possíveis e ações necessárias.
- **Como é cumprido:** Utilização de alertas, feedback sonoro, destaques visuais e mensagens claras na interface.
- **Suposições:** O utilizador está atento aos avisos apresentados pela aplicação.
