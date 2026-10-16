from __future__ import annotations
import base64, json, re, shutil, subprocess, tempfile, urllib.request
from pathlib import Path
from typing import Any
import streamlit as st

APP_NAME = "Novelinha Studio IA"
OLLAMA_URL = "http://localhost:11434/api/chat"
COMFY_URL = "http://127.0.0.1:8188"
SHOTS = ["Plano geral", "Plano médio", "Close emocional", "Primeiro plano", "Plano detalhe", "Sobre o ombro", "Contra-plongée"]
BEATS = [
    ("Gancho", "Uma revelação inesperada interrompe a rotina.", "Comece com uma frase que gere curiosidade nos primeiros 2 segundos."),
    ("Contexto", "Mostre o que a personagem pode perder.", "Apresente o conflito sem explicar tudo de uma vez."),
    ("Confronto", "Duas personagens discordam e escondem informações.", "Use falas curtas e uma reação visual clara."),
    ("Pista", "Um objeto ou mensagem muda a interpretação dos fatos.", "Plante uma pista concreta que será importante depois."),
    ("Escalada", "A pressão aumenta e alguém toma uma decisão ruim.", "Aumente o risco em relação à cena anterior."),
    ("Virada", "A protagonista descobre uma informação contraditória.", "Recontextualize uma fala ou gesto anterior."),
    ("Escolha", "A personagem precisa escolher entre segurança e verdade.", "Mostre a escolha por ação, não só por explicação."),
    ("Revelação", "Uma pessoa inesperada aparece com prova decisiva.", "Entregue uma resposta parcial e abra uma nova pergunta."),
    ("Cliffhanger", "Uma última frase muda tudo e corta antes da resposta.", "Termine com suspense e um motivo para assistir ao próximo episódio."),
]

def slug(text: str) -> str:
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE).strip().replace(" ", "-")
    return (text[:70] or "novelinha").lower()

def scene_template(index: int, count: int, premise: str, genre: str, protagonist: str) -> dict[str, Any]:
    beat = BEATS[min(round(index * (len(BEATS) - 1) / max(count - 1, 1)), len(BEATS) - 1)]
    title, action, direction = beat
    return {"title": f"Cena {index + 1} — {title}", "duration": 5 if index == 0 else 7,
            "shot": SHOTS[2 if title in ("Gancho", "Virada", "Revelação", "Cliffhanger") else 1],
            "setting": "Ambiente dramático coerente com a história; luz cinematográfica e fundo sem distrações.",
            "action": f"{action} Contexto da história: {premise}",
            "dialogue": f'{protagonist}: "Eu preciso descobrir a verdade."' if title in ("Gancho", "Confronto", "Cliffhanger") else "",
            "narration": direction if title in ("Gancho", "Cliffhanger") else "", "image_prompt": "", "image_b64": ""}

def make_prompt(project: dict[str, Any], scene: dict[str, Any]) -> str:
    chars = project.get("characters", [])
    details = "\n".join(f"- {c.get('name','Personagem')}: {c.get('appearance','')} Roupa: {c.get('clothing','')}. Personalidade: {c.get('personality','')}." for c in chars)
    if not details: details = "Descreva personagens realistas e mantenha sua aparência igual nas demais cenas."
    return (f"Vertical 9:16, cinematic short drama still, genre {project.get('genre','drama')}. "
            f"Scene: {scene.get('setting','')}. Action: {scene.get('action','')}. Camera framing: {scene.get('shot','Close emocional')}. "
            f"Characters (keep identical face, age, hairstyle, skin tone and clothes in every shot):\n{details}\n"
            "Emotional facial expression, realistic lighting, detailed composition, natural hands, no text, no watermark.")

def fallback_story(premise: str, genre: str, protagonist: str, count: int) -> dict[str, Any]:
    project = {"app": APP_NAME, "version": 1, "title": premise[:80] or "Minha novelinha", "premise": premise,
        "genre": genre, "format": "9:16", "characters": [
        {"name": protagonist, "appearance": "Pessoa adulta; traços faciais distintos e naturais.", "clothing": "Roupa contemporânea consistente entre cenas.", "personality": "Determinada, guarda um segredo."},
        {"name": "Antagonista", "appearance": "Pessoa adulta; olhar expressivo.", "clothing": "Paleta escura e consistente.", "personality": "Carismático, esconde informações."}], "scenes": []}
    project["scenes"] = [scene_template(i, count, premise, genre, protagonist) for i in range(count)]
    for scene in project["scenes"]: scene["image_prompt"] = make_prompt(project, scene)
    return project

def generate_with_ollama(premise: str, genre: str, protagonist: str, count: int, model: str) -> dict[str, Any]:
    system = ("Você é roteirista de novelinhas verticais viciantes para vídeos curtos. Responda SOMENTE JSON válido, "
        "com chaves title, premise, genre, characters (array de name, appearance, clothing, personality), "
        "scenes (array de title, duration, shot, setting, action, dialogue, narration). "
        "Cada cena deve avançar a história, variar enquadramentos e terminar a última com cliffhanger. "
        "Não repita ações; diálogos naturais em português brasileiro; duração de 4 a 10 segundos por cena.")
    payload = {"model": model, "stream": False, "format": "json", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Premissa: {premise}\nGênero: {genre}\nProtagonista: {protagonist}\nCenas: {count}."}]}
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as response: data = json.loads(response.read().decode("utf-8"))
    raw = json.loads(data["message"]["content"])
    project = {"app": APP_NAME, "version": 1, "title": raw.get("title", premise[:80]), "premise": premise,
        "genre": genre, "format": "9:16", "characters": raw.get("characters", []), "scenes": raw.get("scenes", [])[:count]}
    if not project["scenes"]: raise ValueError("A IA não retornou cenas.")
    for scene in project["scenes"]:
        for key, default in {"duration": 6, "shot": "Plano médio", "image_b64": "", "setting": "", "action": "", "dialogue": "", "narration": ""}.items():
            scene.setdefault(key, default)
        scene["image_prompt"] = make_prompt(project, scene)
    return project

def captions_srt(scenes: list[dict[str, Any]]) -> str:
    def stamp(sec: float) -> str:
        ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    output, current = [], 0.0
    for i, scene in enumerate(scenes, 1):
        text = str(scene.get("dialogue") or scene.get("narration") or "").strip()
        dur = max(1.0, float(scene.get("duration", 6)))
        if text: output.extend([str(i), f"{stamp(current)} --> {stamp(current + dur)}", text, ""])
        current += dur
    return "\n".join(output).strip() + "\n"

def export_video(project: dict[str, Any], use_captions: bool = True) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg: raise RuntimeError("FFmpeg não encontrado. Instale-o ou adicione ffmpeg.exe ao PATH.")
    scenes = project.get("scenes", [])
    if not scenes: raise ValueError("O projeto não tem cenas.")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc: raise RuntimeError("Instale Pillow com: pip install Pillow") from exc
    with tempfile.TemporaryDirectory(prefix="novelinha_") as td:
        root = Path(td); inputs = []
        for i, scene in enumerate(scenes):
            image_path = root / f"scene_{i:03}.png"; raw = scene.get("image_b64", "")
            if raw:
                try:
                    image_path.write_bytes(base64.b64decode(raw))
                    with Image.open(image_path) as check: check.verify()
                except Exception: raw = ""
            if not raw:
                img = Image.new("RGB", (720, 1280), (21 + i * 5 % 50, 25, 46 + i * 7 % 90)); draw = ImageDraw.Draw(img)
                try: font = ImageFont.truetype("arial.ttf", 38)
                except OSError: font = ImageFont.load_default()
                draw.text((45, 520), str(scene.get("title", f"Cena {i + 1}"))[:50], fill="white", font=font)
                draw.text((45, 600), "Adicione uma imagem para esta cena", fill=(220, 205, 235), font=font); img.save(image_path)
            inputs.extend(["-loop", "1", "-t", str(max(1, float(scene.get("duration", 6)))), "-i", str(image_path)])
        filters = [f"[{i}:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,format=yuv420p[v{i}]" for i in range(len(scenes))]
        filters.append("".join(f"[v{i}]" for i in range(len(scenes))) + f"concat=n={len(scenes)}:v=1:a=0[vcat]")
        srt = captions_srt(scenes) if use_captions else ""
        if srt.strip():
            (root / "captions.srt").write_text(srt, encoding="utf-8"); filters.append("[vcat]subtitles=captions.srt[vout]")
        else: filters.append("[vcat]null[vout]")
        cmd = [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[vout]", "-r", "30", "-pix_fmt", "yuv420p"]
        output = root / "novelinha.mp4"
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart", str(output)]
        run = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900)
        if run.returncode != 0 or not output.exists(): raise RuntimeError("Falha no FFmpeg: " + (run.stderr or run.stdout or "erro desconhecido")[-1800:])
        return output.read_bytes()

st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide")
st.title("🎬 Novelinha Studio IA")
st.caption("Roteiros, personagens consistentes, storyboard e vídeo vertical 9:16 — focado em uso local no Windows.")
if "project" not in st.session_state: st.session_state.project = fallback_story("O segredo que mudou tudo", "Drama e suspense", "Lívia", 5)
project = st.session_state.project

with st.sidebar:
    st.header("Nova história")
    premise = st.text_area("Premissa", project.get("premise", ""), height=100, help="Ex.: Uma empregada descobre que é a herdeira da família.")
    genres = ["Drama e suspense", "Romance", "Traição", "Vingança", "Mistério", "Comédia romântica", "Fantasia"]
    genre = st.selectbox("Gênero", genres, index=genres.index(project.get("genre")) if project.get("genre") in genres else 0)
    protagonist = st.text_input("Protagonista", "Lívia")
    count = st.slider("Número de cenas", 3, 12, min(9, max(3, len(project.get("scenes", [])))))
    model = st.text_input("Modelo Ollama", "qwen2.5:7b")
    if st.button("✨ Gerar roteiro com IA local", use_container_width=True):
        try:
            with st.spinner("Gerando roteiro pelo Ollama..."): project = generate_with_ollama(premise, genre, protagonist, count, model)
            st.session_state.project = project; st.success("Roteiro gerado pelo Ollama."); st.rerun()
        except Exception as exc:
            st.warning(f"Ollama indisponível ({exc}). Criei um roteiro-base editável.")
            st.session_state.project = fallback_story(premise, genre, protagonist, count); st.rerun()
    if st.button("Criar roteiro-base sem IA", use_container_width=True):
        st.session_state.project = fallback_story(premise, genre, protagonist, count); st.rerun()
    st.divider(); st.subheader("Conexões locais")
    st.write("Ollama: http://localhost:11434")
    st.write(f"ComfyUI: {COMFY_URL} (prompts prontos; geração depende da instalação local)")
    st.write("Exportação de vídeo requer FFmpeg.")

left, right = st.columns([1.2, 1])
with left:
    project["title"] = st.text_input("Título do projeto", project.get("title", "Minha novelinha"))
    project["premise"] = st.text_area("Resumo da história", project.get("premise", ""), height=80)
    st.subheader("Personagens — mantenha a mesma descrição")
    for i, char in enumerate(project.get("characters", [])):
        with st.expander(f"{char.get('name', 'Personagem')} · ficha visual", expanded=(i == 0)):
            char["name"] = st.text_input("Nome", char.get("name", ""), key=f"cn{i}")
            char["appearance"] = st.text_area("Rosto, idade aparente, cabelo, pele", char.get("appearance", ""), key=f"ca{i}", height=65)
            char["clothing"] = st.text_area("Roupa e acessórios fixos", char.get("clothing", ""), key=f"cc{i}", height=55)
            char["personality"] = st.text_area("Personalidade", char.get("personality", ""), key=f"cp{i}", height=55)
    if st.button("Atualizar prompts de todas as cenas"):
        for scene in project.get("scenes", []): scene["image_prompt"] = make_prompt(project, scene)
        st.success("Prompts atualizados com as fichas dos personagens.")

with right:
    st.subheader("Storyboard e enquadramentos")
    labels = [f"{i + 1}. {s.get('title','Cena')}" for i, s in enumerate(project.get("scenes", []))]
    selected = st.selectbox("Cena para editar", range(len(labels)), format_func=lambda n: labels[n]) if labels else None
    if selected is not None:
        scene = project["scenes"][selected]
        scene["title"] = st.text_input("Título da cena", scene.get("title", ""), key=f"title{selected}")
        scene["duration"] = st.slider("Duração (segundos)", 2, 15, int(scene.get("duration", 6)), key=f"duration{selected}")
        scene["shot"] = st.selectbox("Enquadramento", SHOTS, index=SHOTS.index(scene.get("shot")) if scene.get("shot") in SHOTS else 0, key=f"shot{selected}")
        scene["setting"] = st.text_area("Ambiente", scene.get("setting", ""), key=f"setting{selected}")
        scene["action"] = st.text_area("Ação", scene.get("action", ""), key=f"action{selected}")
        scene["dialogue"] = st.text_area("Diálogo", scene.get("dialogue", ""), key=f"dialogue{selected}")
        scene["narration"] = st.text_area("Narração", scene.get("narration", ""), key=f"narration{selected}")
        scene["image_prompt"] = st.text_area("Prompt visual (copie para ComfyUI)", scene.get("image_prompt", make_prompt(project, scene)), height=130, key=f"prompt{selected}")
        upload = st.file_uploader("Imagem desta cena (opcional)", type=["png", "jpg", "jpeg", "webp"], key=f"image{selected}")
        if upload:
            scene["image_b64"] = base64.b64encode(upload.getvalue()).decode("ascii")
            st.image(upload, caption="Imagem selecionada", use_container_width=True)
        elif scene.get("image_b64"): st.caption("A cena já tem uma imagem salva no projeto.")
        if st.button("Remover imagem da cena"): scene["image_b64"] = ""; st.rerun()

st.divider(); st.subheader("Exportação e projeto")
c1, c2, c3 = st.columns(3)
with c1:
    st.download_button("Baixar roteiro JSON", json.dumps(project, ensure_ascii=False, indent=2), file_name=f"{slug(project.get('title','novelinha'))}.json", mime="application/json", use_container_width=True)
with c2:
    st.download_button("Baixar legendas SRT", captions_srt(project.get("scenes", [])), file_name="legendas.srt", mime="text/plain", use_container_width=True)
with c3:
    loaded = st.file_uploader("Abrir projeto JSON", type=["json"], key="load_project")
    if loaded and st.button("Carregar projeto"):
        try:
            data = json.loads(loaded.getvalue().decode("utf-8"))
            if not isinstance(data.get("scenes"), list): raise ValueError("O JSON não contém uma lista de cenas.")
            st.session_state.project = data; st.rerun()
        except Exception as exc: st.error(f"Projeto inválido: {exc}")

if st.button("🎞️ Renderizar MP4 vertical", type="primary", use_container_width=True):
    try:
        with st.spinner("Renderizando vídeo. Imagens ausentes serão substituídas por cartões de cena..."): video = export_video(project)
        st.video(video)
        st.download_button("Baixar MP4", video, file_name=f"{slug(project.get('title','novelinha'))}.mp4", mime="video/mp4")
    except Exception as exc: st.error(str(exc))
st.caption("Use imagens e vozes com licença adequada. O app não publica automaticamente nas plataformas; revise o vídeo antes de postar.")
