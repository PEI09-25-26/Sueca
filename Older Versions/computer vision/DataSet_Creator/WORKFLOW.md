# Card Dataset Creator - Complete Workflow

## Overview
Sistema completo para criar um dataset de cartas de Sueca e treinar um modelo YOLOv8 de classificação.

## Quick Start Guide

### Passo 1: Capturar Imagens das Cartas
```bash
cd DataSet_Creator
python3 main.py
```

**Durante a captura:**
- Escolha o método de captura (usb/ip/file)
- Digite o nome da classe (ex: `as_copas`)
- Posicione a carta na frente da câmera
- Pressione `s` para salvar as imagens detectadas
- Pressione `c` para trocar de classe
- Pressione `q` para sair

**Meta de captura:**
- 50-100 imagens por carta mínimo
- 100-200 imagens recomendado
- Varie ângulos, iluminação e posições

### Passo 2: Dividir Dataset (Train/Val Split)
```bash
python3 split_dataset.py
```

Isso criará:
```
dataset_split/
├── train/     # 80% das imagens
└── val/       # 20% das imagens
```

### Passo 3: Treinar Modelo YOLOv8
```bash
# Instalar dependências (se ainda não instalou)
pip install ultralytics

# Treinar
python3 train_yolov8_classifier.py
```

O modelo treinado será salvo em:
- `runs/classify/sueca_cards_classifier/weights/best.pt`

## Estrutura de Arquivos

```
DataSet_Creator/
├── main.py                        # Script principal para captura
├── split_dataset.py               # Split train/val
├── train_yolov8_classifier.py     # Treinar YOLOv8
├── README_DATASET.md              # Documentação detalhada
├── camera.py                      # Módulo de câmera
├── opencv.py                      # Detector OpenCV
├── dataset/                       # Imagens capturadas (raw)
│   ├── as_copas/
│   ├── 7_copas/
│   └── ...
└── dataset_split/                 # Dataset dividido (train/val)
    ├── train/
    │   ├── as_copas/
    │   ├── 7_copas/
    │   └── ...
    └── val/
        ├── as_copas/
        ├── 7_copas/
        └── ...
```

## 🃏 Nomenclatura de Classes (40 cartas de Sueca)

### Copas (♥)
- `as_copas`, `7_copas`, `rei_copas`, `valete_copas`, `dama_copas`
- `6_copas`, `5_copas`, `4_copas`, `3_copas`, `2_copas`

### Espadas (♠)
- `as_espadas`, `7_espadas`, `rei_espadas`, `valete_espadas`, `dama_espadas`
- `6_espadas`, `5_espadas`, `4_espadas`, `3_espadas`, `2_espadas`

### Ouros (♦)
- `as_ouros`, `7_ouros`, `rei_ouros`, `valete_ouros`, `dama_ouros`
- `6_ouros`, `5_ouros`, `4_ouros`, `3_ouros`, `2_ouros`

### Paus (♣)
- `as_paus`, `7_paus`, `rei_paus`, `valete_paus`, `dama_paus`
- `6_paus`, `5_paus`, `4_paus`, `3_paus`, `2_paus`

## ⚙️ Configurações Importantes

### main.py
```python
detector = CardDetector(debug=True, min_area=10000)
```
- `min_area`: área mínima para detectar uma carta (ajuste se necessário)
- `debug`: mostrar informações de debug

### split_dataset.py
```python
TRAIN_RATIO = 0.8  # 80% train, 20% val
RANDOM_SEED = 42   # Para reprodutibilidade
```

### train_yolov8_classifier.py
```python
MODEL_SIZE = 'n'      # 'n', 's', 'm', 'l', 'x'
EPOCHS = 100
IMAGE_SIZE = 224
BATCH_SIZE = 16
```

## 📊 Métricas de Qualidade do Dataset

### Bom Dataset
- ✅ Pelo menos 50-100 imagens por classe
- ✅ Variação de ângulos (0°, 15°, 30°, 45°, etc.)
- ✅ Variação de iluminação (luz natural, artificial, sombras)
- ✅ Variação de distância (perto, longe)
- ✅ Diferentes fundos
- ✅ Imagens nítidas (não borradas)

### Dataset Ruim
- ❌ Menos de 30 imagens por classe
- ❌ Todas as imagens no mesmo ângulo
- ❌ Todas com a mesma iluminação
- ❌ Imagens borradas ou de baixa qualidade
- ❌ Distribuição desigual entre classes

## 🎯 Dicas para Melhor Precisão

1. **Capture mais imagens de cartas difíceis**
   - Cartas similares (ex: 6 vs 9, dama vs valete)
   - Cartas com símbolos pequenos

2. **Augmentação durante captura**
   - Rotação: 0°, 15°, 30°, 45°, 90°, 180°, 270°
   - Iluminação: luz natural, artificial, sombras
   - Distância: perto (carta ocupa 80% do frame) a longe (30% do frame)
   - Fundo: branco, preto, madeira, tecido

3. **Qualidade > Quantidade**
   - 100 imagens variadas > 500 imagens similares

4. **Validação visual**
   - Revise as imagens capturadas periodicamente
   - Delete imagens borradas ou com má detecção

## 🔍 Troubleshooting

### Problema: Cartas não detectadas
**Solução:**
- Melhore a iluminação
- Use fundo contrastante
- Ajuste `min_area` no CardDetector

### Problema: Múltiplas detecções da mesma carta
**Solução:**
- Normal! Isso adiciona variação
- Certifique-se que as detecções são suficientemente diferentes
- Se for um problema, aumente `min_area`

### Problema: Imagens borradas
**Solução:**
- Estabilize a câmera
- Aguarde a carta ficar imóvel antes de salvar
- Melhore a iluminação

### Problema: Baixa precisão do modelo
**Solução:**
- Capture mais imagens (especialmente das classes com erro)
- Aumente variação de ângulos e iluminação
- Treine por mais epochs
- Use modelo maior (YOLOv8s ou YOLOv8m)

## 📈 Próximos Passos Após Treino

### 1. Testar o Modelo
```python
from ultralytics import YOLO

model = YOLO('runs/classify/sueca_cards_classifier/weights/best.pt')

# Testar em uma imagem
results = model.predict('test_card.jpg')
print(results[0].probs.top1)  # Classe predita
print(results[0].probs.top1conf)  # Confiança
```

### 2. Integrar no Sistema de Jogo
```python
from yolo import CardClassifier

classifier = CardClassifier(
    model_path='runs/classify/sueca_cards_classifier/weights/best.pt'
)

# Classificar carta detectada
class_label, confidence = classifier.classify(flat_card_image)
```

### 3. Melhorar Continuamente
- Capture mais imagens de cartas com erros
- Re-treinar com dataset expandido
- Testar em condições reais de jogo

## 📚 Recursos Adicionais

- [Ultralytics YOLOv8 Docs](https://docs.ultralytics.com/)
- [YOLOv8 Classification](https://docs.ultralytics.com/tasks/classify/)
- [OpenCV Card Detection Tutorial](https://opencv.org/)

## ✅ Checklist Completo

- [ ] Instalar dependências (`pip install ultralytics opencv-python`)
- [ ] Capturar pelo menos 50 imagens por carta (40 classes × 50 = 2000 imagens)
- [ ] Revisar qualidade das imagens capturadas
- [ ] Executar `split_dataset.py` para criar train/val split
- [ ] Treinar modelo com `train_yolov8_classifier.py`
- [ ] Validar precisão do modelo (target: >95% top-1 accuracy)
- [ ] Testar modelo em imagens reais
- [ ] Integrar modelo no sistema de jogo
- [ ] Coletar feedback e melhorar dataset conforme necessário

---

**Boa sorte com o seu dataset de cartas de Sueca! 🃏🎯**
