import streamlit as st
import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch

    @st.cache_resource
    def load_model():
        base_model = "Qwen/Qwen2.5-1.5B-Instruct"

        # --- GPU ONLY ---
        if not torch.cuda.is_available():
            st.error("❌ No NVIDIA GPU detected.\n\nThis version requires CUDA GPU and cannot run on CPU.")
            st.stop()

        device = "cuda"
        dtype = torch.float16

        progress = st.progress(0)
        msg = st.empty()

        # --- Load Base Model ---
        msg.text("📥 Loading base model on GPU...")
        progress.progress(25)

        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=dtype,
            device_map="cuda",     # Force GPU
        )

        # --- Load LoRA ---
        progress.progress(50)
        lora_path = project_root / "qwen_lora_adapter"

        if lora_path.exists():
            msg.text("📥 Loading LoRA adapter onto GPU...")
            model = PeftModel.from_pretrained(model, str(lora_path))
        else:
            msg.text("⚠️ LoRA adapter not found, using base model")

        # --- Load Tokenizer ---
        progress.progress(70)
        msg.text("📥 Loading tokenizer...")

        tokenizer = AutoTokenizer.from_pretrained(base_model)

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model.config.pad_token_id = tokenizer.pad_token_id

        # --- Warmup on GPU ---
        progress.progress(85)
        msg.text("🔥 Warming up model (GPU)...")
        try:
            test_input = tokenizer(
                "<|im_start|>user\nhello<|im_end|>\n<|im_start|>assistant\n",
                return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                model.generate(**test_input, max_new_tokens=5)
        except:
            pass

        progress.progress(100)
        msg.text("✅ Model Ready on GPU!")

        return model, tokenizer

    # ================ CHAT FUNCTION (GPU ONLY) ================
    def chat_with_model(model, tokenizer, prompt, max_new_tokens=400, temperature=0.7):

        if not torch.cuda.is_available():
            st.error("❌ GPU required for inference.")
            st.stop()

        device = "cuda"

        # Build ChatML prompt
        chatml_prompt = (
            f"<|im_start|>user\n{prompt}\n<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

        inputs = tokenizer(chatml_prompt, return_tensors="pt").to(device)

        eos_token = tokenizer.convert_tokens_to_ids("<|im_end|>")
        if eos_token is None:
            eos_token = tokenizer.eos_token_id

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=False,
                eos_token_id=eos_token,
                pad_token_id=tokenizer.pad_token_id,
            )

        generated = output[0][inputs["input_ids"].shape[1]:]
        text = tokenizer.decode(generated, skip_special_tokens=True)

        if "<|im_end|>" in text:
            text = text.split("<|im_end|>")[0]

        return text.strip()

except ImportError:
    st.error("Missing dependencies. Install: pip install transformers torch peft")
    st.stop()

st.set_page_config(
    page_title="科学导师智能问答系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式 - 温馨教育风格
st.markdown("""
<style>
    /* 彻底隐藏 Streamlit 菜单栏、头部和页脚 */
    #MainMenu {visibility: hidden; height: 0; display: none !important;}
    header {visibility: hidden; height: 0 !important; display: none !important;}
    footer {visibility: hidden; height: 0 !important; display: none !important;}
    
    /* 隐藏右上角的所有按钮和菜单 */
    .stDeployButton {display: none !important;}
    [data-testid="stHeader"] {visibility: hidden !important; height: 0 !important; display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    
    /* 隐藏菜单按钮和设置按钮 */
    button[title="View app source"] {display: none !important;}
    button[title="Get help"] {display: none !important;}
    button[title="Deploy"] {display: none !important;}
    button[kind="header"] {display: none !important;}
    
    /* 移除头部占用的空间 */
    .stApp > header {
        display: none !important;
    }
    
    /* 调整主内容区域，移除头部占用的空间 */
    .stApp {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* 隐藏 Streamlit 的品牌标识 */
    #stDecoration {display: none !important;}
    
    /* 主色调 - 温暖的蓝色和米色 */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
    }
    
    /* 标题样式 */
    .main-title {
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
        color: #2c3e50;
        text-align: center;
        padding: 20px 0;
        margin-bottom: 30px;
    }
    
    /* 卡片样式 */
    .chat-message {
        padding: 15px 20px;
        border-radius: 12px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    
    .assistant-message {
        background: #ffffff;
        border-left: 4px solid #3498db;
        margin-right: 20%;
    }
    
    /* 侧边栏样式 */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
    }
    
    /* 按钮样式 */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* 输入框样式 */
    .stTextArea>div>div>textarea {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        padding: 12px;
    }
    
    /* 学科标签样式 */
    .subject-tag {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 14px;
        margin: 5px;
        font-weight: 500;
    }
    
    .physics { background: #e3f2fd; color: #1976d2; }
    .chemistry { background: #fff3e0; color: #f57c00; }
    .biology { background: #e8f5e9; color: #388e3c; }
</style>
""", unsafe_allow_html=True)

# 辅助函数：检测并渲染LaTeX公式
def render_latex(text):
    """检测文本中的LaTeX公式并渲染（Streamlit会自动渲染LaTeX）"""
    # Streamlit的st.markdown会自动渲染LaTeX，所以这里只需要确保格式正确
    # 将 $$...$$ 转换为换行格式以便更好显示
    text = re.sub(r'\$\$(.*?)\$\$', r'\n\n$$\n\1\n$$\n\n', text, flags=re.DOTALL)
    return text

# 辅助函数：检测意图
def detect_intent(question):
    """简单的意图识别"""
    question_lower = question.lower()
    if any(word in question_lower for word in ['解释', '什么是', '概念', '定义', '含义']):
        return "概念解释", "📖"
    elif any(word in question_lower for word in ['求解', '计算', '题目', '习题', '怎么做']):
        return "习题求解", "✏️"
    elif any(word in question_lower for word in ['文献', '论文', '研究', '综述', '参考']):
        return "文献综述", "📚"
    else:
        return "一般问答", "💬"

# 初始化session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model_loaded" not in st.session_state:
    st.session_state.model_loaded = False
if "model" not in st.session_state:
    st.session_state.model = None
if "tokenizer" not in st.session_state:
    st.session_state.tokenizer = None

# 侧边栏配置
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h2 style='color: #2c3e50; margin-bottom: 10px;'>⚙️ 学习设置</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # 学科选择
    subject = st.selectbox(
        "选择学科",
        ["物理", "化学", "生物", "综合"],
        help="选择您要学习的学科领域"
    )
    
    # 难度级别
    level = st.selectbox(
        "难度级别",
        ["初中", "高中", "大学入门"],
        help="选择适合您的学习难度"
    )
    
    # 学习模式
    mode = st.radio(
        "学习模式",
        ["概念解释", "习题求解", "文献查阅", "自由问答"],
        help="选择您需要的帮助类型"
    )
    
    st.divider()
    
    # 模型参数调整
    st.markdown("**高级设置**")
    max_tokens = st.slider("回答长度", 50, 500, 200, 50, help="设置回答的最大长度，越小越快")
    temperature = st.slider("创造性", 0.1, 1.0, 0.1, 0.1, help="控制回答的随机性，目前使用最快模式")
    
    st.divider()
    
    # 清空对话按钮
    if st.button("🗑️ 清空对话历史", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    # 关于信息
    st.markdown("""
    ---
    <div style='font-size: 12px; color: #7f8c8d; text-align: center;'>
        <p>科学导师智能问答系统</p>
        <p>支持LaTeX公式渲染</p>
        <p>提供深度学术辅导</p>
    </div>
    """, unsafe_allow_html=True)

# 主界面
st.markdown("""
<div class='main-title'>
    <h1 style='font-size: 2.5em; margin-bottom: 10px;'>📚 科学导师智能问答系统</h1>
    <p style='font-size: 1.1em; color: #7f8c8d;'>您的专属科学学习助手，提供深度、可验证的学术辅导</p>
</div>
""", unsafe_allow_html=True)

# 加载模型
if not st.session_state.model_loaded:
    try:
        st.session_state.model, st.session_state.tokenizer = load_model()
        st.session_state.model_loaded = True
    except Exception as e:
        st.error(f"模型加载失败: {str(e)}")
        st.info("请确保已正确安装所有依赖，并检查模型路径是否正确")
        st.stop()

# 显示欢迎消息
if len(st.session_state.messages) == 0:
    st.info("""
    👋 **欢迎使用科学导师智能问答系统！**
    
    我可以帮助您：
    - 📖 **概念解释**：深入理解科学概念和原理
    - ✏️ **习题求解**：提供详细的解题步骤和推导过程
    - 📚 **文献查阅**：推荐相关论文和教材章节
    - 💬 **自由问答**：回答您的任何科学问题
    
    请在下方输入您的问题，我会为您提供详细的解答。
    """)

# 显示对话历史
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        intent = message.get("intent", "一般问答")
        icon = message.get("icon", "💬")
        
        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(f"**{icon} {intent}**")
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                # 渲染LaTeX公式（Streamlit自动支持LaTeX渲染）
                rendered_content = render_latex(content)
                # 使用st.markdown渲染，支持LaTeX
                st.markdown(rendered_content, unsafe_allow_html=False)
                
                # 显示资源链接（如果有）
                if "resources" in message:
                    st.markdown("---")
                    st.markdown("**📚 推荐阅读：**")
                    for resource in message["resources"]:
                        if resource.get('url') and resource['url'] != '#':
                            st.markdown(f"- [{resource['title']}]({resource['url']})")
                        else:
                            st.markdown(f"- {resource['title']} (链接待配置)")

# 用户输入
user_input = st.chat_input("请输入您的问题...")

if user_input:
    # 检测意图
    intent, icon = detect_intent(user_input)
    
    # 添加用户消息
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "intent": intent,
        "icon": icon
    })
    
    # 显示用户消息
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**{icon} {intent}**")
        st.markdown(user_input)
    
    # 生成回复 - 使用流式生成，逐步显示结果
    with st.chat_message("assistant", avatar="🤖"):
        try:
            # 构建上下文提示（简化提示，加快速度）
            context_prompt = f"你是{subject}导师，为{level}学生解答。"
            if mode == "概念解释":
                context_prompt += "简要解释概念和例子。"
            elif mode == "习题求解":
                context_prompt += "提供解题步骤。"
            elif mode == "文献查阅":
                context_prompt += "简要解答并推荐资源。"
            
            full_prompt = f"{context_prompt}\n\n问题：{user_input}"
            
            # 调用模型生成回答
            with st.spinner("正在思考中..."):
                response = chat_with_model(
                    st.session_state.model,
                    st.session_state.tokenizer,
                    full_prompt,
                    max_new_tokens=max_tokens,
                    temperature=temperature
                )
            
            # 渲染结果
            rendered_response = render_latex(response)
            st.markdown(rendered_response, unsafe_allow_html=False)
            
            # 如果是文献查阅模式，添加资源链接占位
            if mode == "文献查阅":
                st.markdown("---")
                st.markdown("**📚 推荐阅读：**")
                st.info("💡 资源链接功能需要后端API支持，当前为演示模式")
            
            # 添加助手消息到历史
            assistant_msg = {
                "role": "assistant",
                "content": response
            }
            
            if mode == "文献查阅":
                assistant_msg["resources"] = [
                    {"title": "相关论文（示例）", "url": "#"},
                    {"title": "教材章节（示例）", "url": "#"}
                ]
            
            st.session_state.messages.append(assistant_msg)
                
        except Exception as e:
            error_msg = f"抱歉，处理您的问题时出现了错误：{str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; font-size: 0.9em; padding: 20px 0;'>
    <p>科学导师智能问答系统 | 支持物理、化学、生物多学科问答</p>
    <p>基于LoRA微调的Qwen2.5模型 | 提供深度学术辅导</p>
</div>
""", unsafe_allow_html=True)



