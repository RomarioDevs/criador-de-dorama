# Novelinha Studio IA

Aplicativo local em português para criar roteiros de novelinhas verticais, organizar personagens, montar storyboard e exportar vídeos MP4 9:16 para TikTok, Kwai, Reels e Shorts.

## Recursos
- Roteiro-base editável sem IA e geração opcional com Ollama local.
- Cenas com ação, ambiente, diálogo, narração, duração, enquadramento e prompt visual.
- Fichas de personagens reaproveitadas nos prompts para ajudar a manter a continuidade visual.
- Upload de imagens por cena, salvar/abrir projeto JSON e exportar legendas SRT.
- Renderização MP4 vertical H.264 usando FFmpeg; cenas sem imagens recebem cartões temporários.
- Nenhuma chave de API paga é obrigatória.

## Instalação no Windows
1. Instale Python 3.10+ em https://www.python.org/downloads/.
2. Instale FFmpeg e adicione `ffmpeg.exe` ao PATH.
3. Opcional: instale Ollama em https://ollama.com/download e rode `ollama pull qwen2.5:7b`.
4. Dê dois cliques em `run_windows.bat`. A primeira instalação precisa de internet para baixar dependências.
5. O programa abre no navegador. Crie um roteiro, revise as cenas, adicione imagens e renderize o MP4.

## IA e personagens
Ollama gera o roteiro no próprio PC. As descrições de rosto, cabelo, roupa e personalidade são incluídas nos prompts de cada cena para ajudar a preservar a identidade visual. Isso não garante rostos idênticos: para mais consistência, use imagens de referência num workflow do ComfyUI, gere as imagens e carregue-as nas cenas correspondentes. O aplicativo fornece prompts para ComfyUI, mas não executa um workflow de imagem automaticamente nesta versão.

## Limitações atuais
- Não publica automaticamente no TikTok, Kwai, Instagram ou YouTube.
- Não gera a imagem a partir do prompt por conta própria; aceita imagens locais e exporta o vídeo.
- A narração aparece no roteiro/SRT, mas síntese de voz automática ainda não está implementada.
- A saída padrão é 720×1280 a 30 fps; confirme suporte ao filtro `subtitles` na sua instalação do FFmpeg para que a legenda seja incorporada no vídeo.
- Verifique direitos de imagem, voz, música e licenças dos modelos antes de publicar.

## Testes
Execute `python -m unittest discover -s tests -v`. Os testes cobrem roteiro, prompts, legendas e exportação vertical; o teste do MP4 é pulado se FFmpeg/ffprobe não estiverem instalados.

## Licença
MIT. Consulte `LICENSE`.
