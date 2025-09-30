import streamlit as st
import cv2
import os
import time
import random

from utils import *

# CRITICAL: Set OpenCV threading to single thread BEFORE importing MTCNN
cv2.setNumThreads(0)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from mtcnn.mtcnn import MTCNN
from streamlit_utils import *

# Page config
st.set_page_config(
    page_title="Outfit Anyway - Virtual Try-On",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize face detector ONCE using session state
@st.cache_resource
def get_face_detector():
    """Initialize face detector once and cache it"""
    return MTCNN()

face_detector = get_face_detector()


# Define processing functions at module level (before they're called)
def process_tryon(cloth_image, pose_image, high_resolution, client_ip):
    """Process virtual try-on request"""
    pose_id = os.path.basename(pose_image).split(".")[0]
    cloth_id = int(os.path.basename(cloth_image).split(".")[0])
    
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    try:
        with progress_placeholder:
            progress_bar = st.progress(0)
        
        status_placeholder.text("⏳ Uploading image...")
        progress_bar.progress(10)
        
        timeId = int(str(time.time()).replace(".", "")) + random.randint(1000, 9999)
        upload_url = upload_pose_img(client_ip, timeId, pose_image)
        
        if len(upload_url) == 0:
            status_placeholder.error("❌ Failed to upload image")
            return
        
        status_placeholder.text("🔄 Submitting task...")
        progress_bar.progress(30)
        
        if high_resolution:
            public_res = publicClothSwap(upload_url, cloth_id, is_hr=1)
        else:
            public_res = publicClothSwap(upload_url, cloth_id, is_hr=0)
        
        if public_res is None:
            status_placeholder.error("❌ Failed to submit task")
            return
        
        status_placeholder.text(f"⏳ Processing... Task ID: {public_res['id']}")
        progress_bar.progress(50)
        
        # Check if mid_result is accessible
        mid_result = public_res['mid_result'] if is_http_resource_accessible(public_res['mid_result']) else None
        
        max_try = 120 * 3
        wait_s = 0.5
        for i in range(max_try):
            time.sleep(wait_s)
            state = getInfRes(public_res['id'])
            
            progress = min(50 + (i / max_try) * 45, 95)
            progress_bar.progress(int(progress))
            
            if state is None:
                status_placeholder.text("⚠️ Task query failed, retrying...")
            elif state['status'] == 'PROCESSING':
                status_placeholder.text(f"🔄 Processing... Query {i}")
            elif state['status'] == 'SUCCEED':
                timestamp = int(time.time() * 1000)
                result_image = state['output1'] + f"?t={timestamp}"
                
                # Download result image locally
                local_result = download_result_image(result_image)
                
                st.session_state.result_image = local_result
                st.session_state.info_text = f"✅ Task finished! {state['msg']}"
                
                progress_bar.progress(100)
                status_placeholder.success("✅ Virtual try-on completed successfully!")
                time.sleep(1)
                st.rerun()
                return
            elif state['status'] == 'FAILED':
                status_placeholder.error(f"❌ Task failed: {state['msg']}")
                return
        
        status_placeholder.warning("⏰ Task timeout. Please try again.")
        
    except Exception as e:
        status_placeholder.error(f"❌ Processing exception: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


def process_pose_change(pose_prompt, pose_changer_image, token):
    """Process pose change request"""
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    try:
        with progress_placeholder:
            progress_bar = st.progress(0)
        
        client_ip = get_client_ip()
        
        status_placeholder.text("⏳ Uploading image...")
        progress_bar.progress(20)
        
        # Upload image if it's a local file
        if isinstance(pose_changer_image, str) and not pose_changer_image.startswith('http'):
            timeId = int(str(time.time()).replace(".", "")) + random.randint(1000, 9999)
            image_url = upload_pose_img(client_ip, timeId, pose_changer_image)
            if not image_url:
                status_placeholder.error("❌ Image upload failed!")
                return
        else:
            image_url = pose_changer_image
        
        status_placeholder.text("🔄 Submitting pose change request...")
        progress_bar.progress(40)
        
        pose_result = public_pose_changer(image_url, pose_prompt)
        if pose_result is None:
            status_placeholder.error("❌ Pose change request failed!")
            return
        
        status_placeholder.text(f"⏳ Processing... Task ID: {pose_result['id']}")
        progress_bar.progress(60)
        
        max_try = 120
        wait_s = 1
        for i in range(max_try):
            time.sleep(wait_s)
            result = get_pose_changer_res(pose_result['id'])
            
            progress = min(60 + (i / max_try) * 35, 95)
            progress_bar.progress(int(progress))
            
            if result is None:
                continue
            elif result['status'] == 'PROCESSING':
                status_placeholder.text(f"🔄 Processing... Query {i}")
                continue
            elif result['status'] == 'SUCCEED':
                # Extract output images
                output_images = []
                for j in range(1, 4):
                    output_key = f'output{j}'
                    if output_key in result and result[output_key] and result[output_key].strip():
                        timestamp = int(time.time() * 1000)
                        img_url = result[output_key] + f"?t={timestamp}"
                        local_img = download_result_image(img_url, f"pose_result_{j}_{int(time.time())}.jpg")
                        if local_img:
                            output_images.append(local_img)
                
                st.session_state.pose_results = output_images
                st.session_state.pose_info = f"✅ Pose change completed! {result.get('msg', '')}"
                
                progress_bar.progress(100)
                status_placeholder.success("✅ Pose change completed successfully!")
                time.sleep(1)
                st.rerun()
                return
            elif result['status'] == 'FAILED':
                status_placeholder.error(f"❌ Pose change failed: {result.get('msg', '')}")
                return
        
        status_placeholder.warning("⏰ Pose change timeout!")
        
    except Exception as e:
        status_placeholder.error(f"❌ Processing exception: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


# Title and description
st.markdown("# 👔 Outfit Anyway: Best Customer Try-On You Ever See")
# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result_image' not in st.session_state:
    st.session_state.result_image = None
if 'info_text' not in st.session_state:
    st.session_state.info_text = ""
if 'pose_results' not in st.session_state:
    st.session_state.pose_results = []
if 'pose_info' not in st.session_state:
    st.session_state.pose_info = ""

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    high_resolution = st.checkbox("High Resolution", value=False)
    st.markdown("---")
    st.markdown("### 📖 Upload Tips")
    tip1, tip2 = get_tips()
    if os.path.exists(tip1):
        st.image(tip1, caption="Tip 1", use_container_width=True)
    if os.path.exists(tip2):
        st.image(tip2, caption="Tip 2", use_container_width=True)

# Main content area
tab1, tab2 = st.tabs(["🎯 Virtual Try-On", "🎭 Pose Changer"])

with tab1:
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.subheader("1️⃣ Choose Clothing")
        cloth_examples = get_cloth_examples(hr=0)
        cloth_hr_examples = get_cloth_examples(hr=1)
        
        if len(cloth_examples) == 0 and len(cloth_hr_examples) == 0:
            st.error("❌ No clothing examples found. Please ensure 'Datas/ClothImgs' directory exists with images.")
            cloth_image = None
        else:
            cloth_option = st.radio("Clothing Type:", ["Standard", "Premium"])
            
            if cloth_option == "Standard" and len(cloth_examples) > 0:
                selected_cloth_idx = st.selectbox(
                    "Select a clothing item:",
                    range(len(cloth_examples)),
                    format_func=lambda x: f"Cloth {os.path.basename(cloth_examples[x]).split('.')[0]}"
                )
                cloth_image = cloth_examples[selected_cloth_idx]
            elif len(cloth_hr_examples) > 0:
                selected_cloth_idx = st.selectbox(
                    "Select a premium clothing item:",
                    range(len(cloth_hr_examples)),
                    format_func=lambda x: f"Cloth {os.path.basename(cloth_hr_examples[x]).split('.')[0]}"
                )
                cloth_image = cloth_hr_examples[selected_cloth_idx]
            else:
                cloth_image = None
            
            if cloth_image and os.path.exists(cloth_image):
                st.image(cloth_image, caption="Selected Clothing", use_container_width=True)
    
    with col2:
        st.subheader("2️⃣ Choose/Upload Photo")
        
        pose_source = st.radio("Photo Source:", ["Example Photos", "Upload Your Own"])
        
        if pose_source == "Example Photos":
            pose_examples = get_pose_examples()
            if len(pose_examples) > 0:
                selected_pose_idx = st.selectbox(
                    "Select a pose:",
                    range(len(pose_examples)),
                    format_func=lambda x: f"Pose {os.path.basename(pose_examples[x]).split('.')[0]}"
                )
                pose_image = pose_examples[selected_pose_idx]
            else:
                st.warning("No pose examples found in 'Datas/PoseImgs' directory.")
                pose_image = None
        else:
            uploaded_file = st.file_uploader("Upload your photo", type=['jpg', 'jpeg', 'png'])
            if uploaded_file is not None:
                # Save uploaded file temporarily
                temp_dir = "tmp"
                os.makedirs(temp_dir, exist_ok=True)
                pose_image = os.path.join(temp_dir, f"uploaded_{int(time.time())}.jpg")
                with open(pose_image, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            else:
                pose_image = None
        
        if pose_image and os.path.exists(pose_image):
            st.image(pose_image, caption="Selected/Uploaded Photo", use_container_width=True)
    
    with col3:
        st.subheader("3️⃣ Generate Result")
        
        if st.button("🚀 Run Virtual Try-On", type="primary", use_container_width=True, disabled=st.session_state.processing):
            if pose_image is None:
                st.error("❌ No pose image found! Please select or upload a photo.")
            elif cloth_image is None:
                st.error("❌ No cloth image found! Please select a clothing item.")
            else:
                # Validate face detection
                try:
                    pose_np = cv2.imread(pose_image)
                    if pose_np is None:
                        st.error("❌ Failed to read image. Please try another image.")
                    else:
                        faces = face_detector.detect_faces(pose_np[:,:,::-1])
                        
                        if len(faces) == 0:
                            st.error("❌ Fatal Error! No face detected! You must upload a human photo, not a clothing photo!")
                        else:
                            x, y, w, h = faces[0]["box"]
                            H, W = pose_np.shape[:2]
                            max_face_ratio = 1/3.3
                            
                            if w/W > max_face_ratio or h/H > max_face_ratio:
                                st.error("❌ Fatal Error! Headshot is not allowed! You must upload a full-body or half-body photo!")
                            else:
                                # Check region (optional - you can remove this if not needed)
                                client_ip = get_client_ip()
                                if not check_region_warp(client_ip):
                                    st.error("❌ Failed! Our server is under maintenance, please try again later.")
                                else:
                                    # Process the request
                                    st.session_state.processing = True
                                    process_tryon(cloth_image, pose_image, high_resolution, client_ip)
                                    st.session_state.processing = False
                except Exception as e:
                    st.error(f"❌ Error processing image: {str(e)}")
                    st.session_state.processing = False
        
        # Display processing info and results
        if st.session_state.info_text:
            st.info(st.session_state.info_text)
        
        if st.session_state.result_image:
            if isinstance(st.session_state.result_image, str) and os.path.exists(st.session_state.result_image):
                st.image(st.session_state.result_image, caption="Result Image", use_container_width=True)
                
                # Download button for result
                with open(st.session_state.result_image, "rb") as file:
                    st.download_button(
                        label="📥 Download Result",
                        data=file,
                        file_name=f"tryon_result_{int(time.time())}.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
            else:
                st.image(st.session_state.result_image, caption="Result Image", use_container_width=True)

with tab2:
    st.subheader("🎭 AI Pose Changer")
    
    # Token input
    pose_token = st.text_input("Access Token", type="password", placeholder="Enter your token...")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### Source Image")
        pose_uploaded = st.file_uploader("Upload image for pose change", type=['jpg', 'jpeg', 'png'], key="pose_upload")
        
        if pose_uploaded is not None:
            temp_dir = "tmp"
            os.makedirs(temp_dir, exist_ok=True)
            pose_changer_image = os.path.join(temp_dir, f"pose_source_{int(time.time())}.jpg")
            with open(pose_changer_image, "wb") as f:
                f.write(pose_uploaded.getbuffer())
            st.image(pose_changer_image, use_container_width=True)
        else:
            # Use result from try-on if available
            if st.session_state.result_image and isinstance(st.session_state.result_image, str) and os.path.exists(st.session_state.result_image):
                pose_changer_image = st.session_state.result_image
                st.image(pose_changer_image, caption="Using try-on result", use_container_width=True)
            else:
                pose_changer_image = None
                st.info("Please upload an image or run virtual try-on first")
    
    with col2:
        st.markdown("#### Pose Change Settings")
        pose_prompt = st.text_area(
            "Pose Change Prompt",
            value="Change the pose: hands on hips.#Change the pose: arms extended.",
            height=100,
            help="Describe the pose changes you want. Separate multiple poses with '#'"
        )
        
        if st.button("✨ Change Pose", type="primary", use_container_width=True, disabled=st.session_state.processing):
            if pose_token != POSEToken:
                st.error("❌ Please input the correct token!")
            elif pose_changer_image is None:
                st.error("❌ Please provide source image first!")
            else:
                st.session_state.processing = True
                process_pose_change(pose_prompt, pose_changer_image, pose_token)
                st.session_state.processing = False
    
    # Display pose change results
    if st.session_state.pose_info:
        st.info(st.session_state.pose_info)
    
    if st.session_state.pose_results:
        st.markdown("#### Results")
        cols = st.columns(3)
        for idx, (col, result_img) in enumerate(zip(cols, st.session_state.pose_results)):
            with col:
                if result_img and os.path.exists(result_img):
                    st.image(result_img, caption=f"Result {idx+1}", use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p>Powered by Outfit Anyway | Built with Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)
