# Requisitos Funcionais e N

## Requisitos Funcionais
- A aplicação deve ser capaz de reconhecer automaticamente as cartas apresentadas à câmara, mesmo quando estas estiverem parcialmente sobrepostas ou inclinadas, garantindo uma identificação precisa e consistente durante toda a partida.
- Deve processar a informação do estado do jogo adquirida pelas cartas reconhecidas e pelo comportamento dos jogadores, para calcular a jogada mais adequada, tendo em conta as regras oficiais da Sueca e a estratégia mais vantajosa possível.
- A aplicação deve comunicar rapidamente ao jogador humano a carta que deve ser jogada, utilizando recursos de áudio claros e não intrusivos, permitindo que o jogador execute a jogada sem confusão ou atraso.
- O sistema deve registar a pontuação individual de cada jogador e a pontuação consolidada das equipas, atualizando essa informação em tempo real para que todos os jogadores tenham conhecimento do estado do jogo.
- Deve implementar mecanismos para detetar erros ou jogadas inválidas, como renúncias (quando um jogador não tem carta da cor pedida), e alertar os jogadores para que estas situações sejam corrigidas conforme as regras.
- Deve armazenar estatísticas do desempenho do jogo, incluindo frequência de jogadas, cartas jogadas por cada jogador, e resultados das partidas, permitindo posteriormente a análise e avaliação dos jogadores.
- A aplicação deve permitir a organização e gestão de torneios, possibilitando o registo de múltiplas partidas, classificação de jogadores e equipas, e acompanhamento do progresso dos torneios.
- Deve permitir a configuração personalizada das regras e modos de jogo, para acomodar variantes regionais da Sueca ou preferências dos jogadores.
- Deve assegurar que todas as interações do sistema com o utilizador sejam intuitivas, fornecendo feedback visual e auditivo durante o jogo para informar sobre o estado atual, jogadas possíveis e ações necessárias.


## Requisitos Não Funcionais
- A aplicação deve ser rápida e eficiente na análise das cartas e na tomada de decisão, garantindo uma resposta fluída e precisa.
- O reconhecimento das cartas deve ser fiável, funcionando bem em diversas condições de iluminação e ângulos variados.
- A aplicação deve preservar a autonomia da bateria, com um consumo de energia moderado durante o uso prolongado.
- Deve funcionar em vários dispositivos móveis comuns, garantindo acessibilidade ao maior número possível de utilizadores.
- As imagens captadas devem ser processadas localmente, sem armazenamento ou envio para servidores externos, garantindo a privacidade do utilizador.
- A interface deve ser simples, fácil de usar, e suportar comandos de voz para minimizar a interação manual.
- Deve ser resiliente a falhas temporárias, recuperando rapidamente após perda de sinal de imagem ou áudio.
- O funcionamento completo deve ser possível sem ligação à internet, assegurando continuidade durante toda a partida.
- O código deve ser modular e bem documentado, facilitando a manutenção e futuras atualizações.
- Deve ter uma arquitetura que permita adicionar funcionalidades novas no futuro, sem necessidade de reescrever o sistema principal.

