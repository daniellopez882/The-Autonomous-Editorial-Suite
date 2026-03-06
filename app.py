import streamlit as st
from content_generation_crew import ContentGenerationCrew
import time
from datetime import datetime
import markdown

st.set_page_config(
    page_title="QuantumContent | Autonomous Editorial Suite",
    page_icon="🔮",
    layout="wide"
)

# Authentication Check
from auth import check_authentication
if not check_authentication():
    st.stop()

# Custom CSS for Ultra-Premium Look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    :root {
        --primary: #6366f1;
        --secondary: #a855f7;
        --accent: #ec4899;
        --background: #0f172a;
        --glass: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.1);
    }
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        color: #f1f5f9;
    }
    
    .stApp {
        background: radial-gradient(circle at top right, #1e1b4b, #0f172a);
    }
    
    .main-header {
        font-size: 4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        text-align: center;
        letter-spacing: -2px;
    }
    
    .sub-text {
        color: #94a3b8;
        font-size: 1.3rem;
        text-align: center;
        margin-bottom: 4rem;
        font-weight: 300;
    }
    
    .agent-card {
        background: var(--glass);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        padding: 1.5rem;
        border-radius: 20px;
        margin-bottom: 1.2rem;
        border: 1px solid var(--glass-border);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .agent-card:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: var(--primary);
        background: rgba(255, 255, 255, 0.05);
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }
    
    .glass-panel {
        background: var(--glass);
        backdrop-filter: blur(16px);
        border-radius: 24px;
        padding: 2.5rem;
        border: 1px solid var(--glass-border);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 2rem;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        padding: 1rem 2.5rem;
        border-radius: 16px;
        font-weight: 700;
        transition: all 0.3s;
        width: 100%;
        font-size: 1.2rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 35px -10px rgba(99, 102, 241, 0.6);
        background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
    }

    /* Customizing Inputs */
    .stTextInput>div>div>input {
        background: var(--glass) !important;
        border-radius: 12px !important;
        border: 1px solid var(--glass-border) !important;
        color: white !important;
    }

    .stSelectbox>div>div>div {
        background: var(--glass) !important;
        border-radius: 12px !important;
        border: 1px solid var(--glass-border) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize crew
@st.cache_resource
def get_crew():
    return ContentGenerationCrew()

# Header Section
st.markdown('<p class="main-header">QuantumContent 🔮</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Next-Gen Autonomous Editorial Pipeline & Content Forge</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🤖 AI Agent Team")
    agents_info = {
        "Researcher": ("🔍", "Information specialist"),
        "Writer": ("✍️", "Narrative expert"),
        "Editor": ("📝", "Refinement master"),
        "Fact Checker": ("✅", "Accuracy scout"),
        "SEO Guru": ("📈", "Search optimizer"),
        "Viral Catalyst": ("🚀", "Engagement genius")
    }
    
    for agent, (icon, role) in agents_info.items():
        st.markdown(f"""
        <div class="agent-card">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.5rem;">{icon}</span>
                <div>
                    <strong style="color: white;">{agent}</strong><br>
                    <span style="font-size: 0.85rem; color: #94a3b8;">{role}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Main UI
with st.container():
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        topic = st.text_input("🎯 Central Topic / Research Goal", placeholder="e.g., The Future of Sustainable Energy")
    
    with col2:
        content_type = st.selectbox("📄 Format", 
                                  ["Blog Post", "Research Report", "Technical Article", "Newsletter", "Whitepaper"])
    
    with col3:
        tone = st.selectbox("🎭 Narrative Tone", 
                          ["Professional", "Conversational", "Academic", "Humorous", "Inspirational", "Aggressive"])

    if st.button("🚀 IGNITE PIPELINE"):
        if not topic:
            st.error("Please enter a topic.")
        else:
            try:
                crew = get_crew()
                
                with st.status("🎬 Orchestrating Agents...", expanded=True) as status:
                    st.write("🔍 Researcher is scouring the web...")
                    
                    start_time = time.time()
                    result = crew.generate_content(topic, content_type, tone)
                    end_time = time.time()
                    
                    status.update(label="✅ Pipeline Succeeded!", state="complete", expanded=False)
                
                # Results Display
                st.success(f"Generated successfully in {end_time - start_time:.1f} seconds!")
                
                # Score the content
                from quality_scorer import ContentQualityScorer
                scorer = ContentQualityScorer()
                quality_results = scorer.score_content(result["article_body"], topic)
                
                # Save Version
                from content_versioning import ContentVersionControl
                vc = ContentVersionControl()
                version_id = vc.save_version(topic, result["article_body"])
                
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "📄 Article", 
                    "🚀 Viral Catalyst",
                    "📊 Intelligence Stats", 
                    "⭐ Quality Audit", 
                    "📜 History",
                    "🛠️ Markdown"
                ])
                
                with tab1:
                    st.markdown(f"### Tone: {tone}")
                    st.markdown(result["article_body"])
                    
                with tab2:
                    st.markdown("### ⚡ Viral Catalyst Pack")
                    st.info("These hooks and posts are designed to maximize engagement on social platforms.")
                    st.markdown(result["final_content"]) # This contains the viral pack
                
                with tab3:
                    cols = st.columns(3)
                    cols[0].metric("Brain Power", f"{result['agents_used']} Agents")
                    cols[1].metric("Cognitive Steps", result["tasks_completed"])
                    cols[2].metric("Complexity Index", "High")
                
                with tab4:
                    st.markdown(f"### Overall Grade: **{quality_results['grade']}**")
                    st.progress(quality_results['overall_score'] / 100)
                    st.metric("Quality Score", f"{quality_results['overall_score']}/100")
                    
                    st.markdown("#### Precision Metrics")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Readability", quality_results['scores']['readability'])
                    c2.metric("Structure", quality_results['scores']['structure'])
                    c3.metric("Engagement", quality_results['scores']['engagement'])
                    
                    st.markdown("#### Strategic Recommendations")
                    for rec in quality_results['recommendations']:
                        st.info(rec)
                
                with tab5:
                    st.markdown("### Version History")
                    history = vc.get_history(topic)
                    st.table(history)
                
                with tab6:
                    st.code(result["article_body"], language="markdown")
                    
                # Download
                st.download_button(
                    label="📥 Export as Markdown",
                    data=result["article_body"],
                    file_name=f"quantum_content_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.exception(e)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 0.9rem;">
    Powered by <strong>QuantumEngine</strong> & CrewAI • Developed with ❤️ for High-Impact Content
</div>
""", unsafe_allow_html=True)
