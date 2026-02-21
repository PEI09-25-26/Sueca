# Requisitos Não Funcionais

## 1. Rapidez e Eficiência

- **Descrição:** A aplicação deve ser rápida e eficiente na análise das cartas e na tomada de decisão, garantindo uma resposta fluída e precisa.
- **Como é cumprido:** São utilizadas bibliotecas otimizadas (OpenCV e YOLO) conhecidas pelo processamento eficiente em tempo real.
- **Suposições:** O dispositivo tem os recursos mínimos necessários (CPU/GPU compatível).
- **Dependências:** O desempenho depende da qualidade da câmara e da performance do hardware do telemóvel.

## 2. Fiabilidade no Reconhecimento

- **Descrição:** O reconhecimento das cartas deve ser fiável, funcionando bem em condições variadas de iluminação e ângulos.
- **Como é cumprido:** O sistema é treinado com um conjunto de dados diversificado e usa técnicas de pré-processamento para normalizar imagens.
- **Suposições:** O ambiente tem iluminação razoável e as cartas estão dentro do campo de visão da câmara.
- **Dependências:** Pode diminuir em ambientes de baixa luz extrema ou se as cartas estiverem obstruídas.

## 3. Eficiência Energética

- **Descrição:** A aplicação deve preservar a autonomia da bateria.
- **Como é cumprido:** Optimizam-se os ciclos de processamento de frames e desligam-se processos não essenciais durante o jogo.
- **Suposições:** O utilizador inicia o jogo com bateria suficiente.
- **Dependências:** O consumo pode ser maior em telemóveis com baterias degradadas.

## 4. Compatibilidade

- **Descrição:** Deve funcionar em vários dispositivos móveis comuns.
- **Como é cumprido:** O desenvolvimento e os testes focam-se em smartphones Android recentes e populares.
- **Suposições:** Os utilizadores têm dispositivos relativamente atuais.
- **Dependências:** Compatibilidade limitada em modelos muito antigos ou com Android descontinuado.

## 5. Privacidade

- **Descrição:** As imagens são processadas localmente, sem envio ou armazenamento externo.
- **Como é cumprido:** Todo o processamento ocorre no dispositivo e não existem funções de upload externas.
- **Suposições:** O utilizador não altera permissões nem configurações que contrariem este princípio.
- **Dependências:** Bibliotecas externas devem ser avaliadas para garantir ausência de transmissões ocultas.

## 6. Usabilidade

- **Descrição:** A interface deve ser simples, intuitiva e fácil de usar, adaptando-se às boas práticas de usabilidade para aplicações móveis.
- **Como é cumprido:** O design segue os princípios do Material Design e leis de usabilidade reconhecidas, incluindo disposição clara dos elementos, botões acessíveis e navegação facilitada. O sistema prioriza fluxos simples e diretos, minimizando a carga cognitiva do utilizador.
- **Suposições:** O utilizador está familiarizado com interfaces móveis modernas e utiliza um dispositivo com suporte a interface gráfica básica.

## 7. Resiliência a Falhas

- **Descrição:** A aplicação deve recuperar rapidamente de falhas temporárias de imagem ou áudio.
- **Como é cumprido:** Utilizam-se mecanismos automáticos detecçāo e recuperação.
- **Suposições:** Falhas não são prolongadas.
- **Dependências:** A fiabilidade pode ser menor em dispositivos com hardware danificado.

## 8. Manutenibilidade

- **Descrição:** O código deve ser modular e bem documentado.
- **Como é cumprido:** Segue-se uma arquitetura modular e padrões de documentação.
- **Suposições:** O desenvolvimento inclui revisão e atualização dos comentários no código.

## 9. Extensibilidade

- **Descrição:** A arquitetura deve permitir adicionar funcionalidades futuras sem reescrever o sistema principal.
- **Como é cumprido:** Utilização de boas práticas de desacoplamento e interfaces extensíveis.
- **Suposições:** Futuras equipas respeitam a estrutura estabelecida.
  