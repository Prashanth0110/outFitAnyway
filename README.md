# Virtual Try-On App - Simple Local Version

A Streamlit-based virtual try-on application where users upload their clothing and photo images to create try-on results.

## ✨ Features

- 📸 Upload clothing images
- 🧍 Upload your photo
- 🎨 Automatic face detection validation
- 🔄 Generate virtual try-on results
- 📥 Download results
- 💾 All processing done locally (no cloud storage needed)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
streamlit run streamlit_app_fixed.py
```

Or rename the file to `app.py` and run:

```bash
streamlit run app.py
```

### 3. Use the App

1. **Upload Clothing**: Click "Upload Clothing Image" and select a clothing item
2. **Upload Photo**: Click "Upload Your Photo" and select your full-body or half-body photo
3. **Generate**: Click "Generate Try-On" button
4. **Download**: Download your result image

## 📁 File Structure

```
your_project/
├── streamlit_app_fixed.py    # Main application
├── streamlit_utils.py         # Utility functions
├── requirements.txt           # Python dependencies
├── tmp/                       # Temporary files (auto-created)
└── README.md                  # This file
```

## 📋 Requirements

- Python 3.8 or higher
- Webcam or image files for upload
- ~2GB disk space for dependencies

## 🎯 Photo Guidelines

### For Your Photo:
- ✅ Full-body or half-body shot
- ✅ Face clearly visible
- ✅ Stand straight facing camera
- ✅ Good lighting
- ❌ No headshots (too close-up)
- ❌ No group photos

### For Clothing:
- ✅ Clear image of the item
- ✅ Plain background preferred
- ✅ Full view of garment
- ✅ Good lighting

## 🔧 Technical Details

### Face Detection
- Uses MTCNN (Multi-task Cascaded Convolutional Networks)
- Validates face size to ensure full/half-body photos
- Rejects headshots automatically

### Image Processing
- Automatic image validation
- Size optimization
- Format conversion support (JPG, JPEG, PNG)

### Current Limitation
⚠️ **Note**: The current version creates a **simple side-by-side merge** of the clothing and your photo. This is a **placeholder** for demonstration purposes.

**To get actual virtual try-on results**, you need to:
1. Integrate with a virtual try-on API service
2. Replace the `merge_images_simple()` function in `streamlit_app_fixed.py`
3. Or implement your own try-on algorithm

## 🔌 Integrating Actual Try-On API

To connect to a real virtual try-on service:

### Option 1: Use Your Existing API

In `streamlit_app_fixed.py`, replace the `process_tryon_local()` function:

```python
def process_tryon_local(cloth_image_path, pose_image_path, high_resolution):
    # Your API call here
    result_url = call_your_tryon_api(cloth_image_path, pose_image_path)
    
    # Download result
    result_path = download_result_image(result_url)
    st.session_state.result_image = result_path
```

### Option 2: Use Commercial APIs

Popular virtual try-on APIs:
- **Pixelbin.io** - Virtual try-on API
- **Revery.ai** - Fashion AI try-on
- **Vue.ai** - Retail AI solutions
- **Deep Fashion** - Try-on technology

## 🛠️ Customization

### Change Theme Colors

Edit the Streamlit config:

```bash
# Create .streamlit/config.toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### Adjust Image Size Limits

In `streamlit_utils.py`, modify the `validate_image()` function:

```python
if h > 4000 or w > 4000:  # Change these values
    return False, "Image is too large"
```

## 🐛 Troubleshooting

### "Mutex lock failed" Error
✅ Already fixed with `cv2.setNumThreads(0)` at the top of the file

### "No face detected" Error
- Ensure your photo shows your face clearly
- Use a full-body or half-body photo
- Check lighting in your photo

### Images Not Displaying
- Check file format (use JPG, JPEG, or PNG)
- Ensure file size is under 200MB
- Verify image is not corrupted

### Slow Performance
- Reduce image resolution before upload
- Close other applications
- Check system resources (RAM/CPU)

## 📝 To-Do / Roadmap

- [ ] Integrate actual virtual try-on API
- [ ] Add multiple clothing items support
- [ ] Support video try-on
- [ ] Add AR (Augmented Reality) view
- [ ] Social media sharing integration
- [ ] Save favorites/history
- [ ] User accounts and profiles

## 📄 License

MIT License - feel free to modify and use for your projects

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues or questions, please open an issue on GitHub or contact support.

---

**Made with ❤️ using Streamlit**
