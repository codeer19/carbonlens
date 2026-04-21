import { useState, useRef, useCallback, useEffect } from 'react'
import { Camera, Image, FileText, RotateCcw, X, Upload, Search, ArrowRight } from 'lucide-react'
import { scanBill, scanBillBase64, parsePDF } from '../services/api'
import './BillScanner.css'

/**
 * BillScanner — Triple-mode bill scanning component.
 * 
 * Mode 1: "Camera"       — Live webcam capture → /scan/base64
 * Mode 2: "Upload Image" — File upload → /scan (Tesseract OCR + Groq)
 * Mode 3: "Upload PDF"   — PDF upload → /parse (Three-layer parser)
 */
function BillScanner({ onScanComplete }) {
  const [activeMode, setActiveMode] = useState('camera')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  // Camera state
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraError, setCameraError] = useState(null)
  const [capturedImage, setCapturedImage] = useState(null)
  const [facingMode, setFacingMode] = useState('environment')
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  const fileInputRef = useRef(null)

  const acceptTypes = {
    camera: '',
    scan: '.jpg,.jpeg,.png,.webp,.bmp,.tiff,.tif',
    pdf: '.pdf',
  }

  // Camera Functions
  const startCamera = useCallback(async () => {
    setCameraError(null)
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
      }
      const constraints = {
        video: { facingMode: facingMode, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }
      setCameraActive(true)
    } catch (err) {
      console.error('Camera access failed:', err)
      if (err.name === 'NotAllowedError') {
        setCameraError('Camera access denied. Please allow camera permissions in your browser settings.')
      } else if (err.name === 'NotFoundError') {
        setCameraError('No camera found on this device. Try uploading an image instead.')
      } else {
        setCameraError(`Camera error: ${err.message}`)
      }
      setCameraActive(false)
    }
  }, [facingMode])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraActive(false)
  }, [])

  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
    setCapturedImage(dataUrl)
    stopCamera()
  }, [stopCamera])

  const retakePhoto = useCallback(() => {
    setCapturedImage(null)
    setError(null)
    startCamera()
  }, [startCamera])

  const toggleCamera = useCallback(() => {
    setFacingMode(prev => prev === 'environment' ? 'user' : 'environment')
  }, [])

  useEffect(() => {
    if (cameraActive) startCamera()
  }, [facingMode])

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
    }
  }, [])

  // Mode Switch
  const handleModeSwitch = (mode) => {
    stopCamera()
    setCapturedImage(null)
    setActiveMode(mode)
    setFile(null)
    setPreview(null)
    setError(null)
    setCameraError(null)
  }

  // File Handling
  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0]
    if (selected) processSelectedFile(selected)
  }

  const processSelectedFile = (selected) => {
    setError(null)
    if (selected.size > 10 * 1024 * 1024) {
      setError('File too large. Maximum 10 MB.')
      return
    }
    const ext = selected.name.split('.').pop().toLowerCase()
    if (activeMode === 'pdf' && ext !== 'pdf') {
      setError('Please select a PDF file in PDF mode.')
      return
    }
    if (activeMode === 'scan' && !['jpg','jpeg','png','webp','bmp','tiff','tif'].includes(ext)) {
      setError('Please select an image file (JPEG, PNG, WebP, BMP, TIFF).')
      return
    }
    setFile(selected)
    if (activeMode === 'scan') {
      const reader = new FileReader()
      reader.onload = (ev) => setPreview(ev.target.result)
      reader.readAsDataURL(selected)
    } else {
      setPreview(null)
    }
  }

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true) }
  const handleDragLeave = (e) => { e.preventDefault(); setDragOver(false) }
  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) processSelectedFile(dropped)
  }

  // Submit
  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    try {
      let result
      if (activeMode === 'camera') {
        if (!capturedImage) return
        result = await scanBillBase64(capturedImage, 'camera_capture.jpg')
        onScanComplete(result)
      } else if (activeMode === 'scan') {
        if (!file) return
        result = await scanBill(file)
        onScanComplete(result)
      } else {
        if (!file) return
        result = await parsePDF(file)
        if (result.success === false) {
          setError(result.error || 'Could not extract data from this PDF. Please try manual entry or a clearer scan.')
          return
        }
        onScanComplete({
          success: true,
          kwh_consumed: result.kwh_consumed,
          fuel_litres: result.fuel_litres,
          billing_date: result.billing_date,
          total_amount: result.total_amount,
          co2_kg: result.co2_kg,
          bill_type: 'electricity',
          discom_name: result.discom_name || null,
          extraction_method: 'pdf_three_layer',
        })
      }
    } catch (err) {
      setError(err.message || 'Processing failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setFile(null)
    setPreview(null)
    setCapturedImage(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const canSubmit = activeMode === 'camera' ? !!capturedImage : !!file

  return (
    <div className="bill-scanner" id="bill-scanner">
      <div className="scanner-card">
        {/* Mode Toggle */}
        <div className="mode-toggle" id="mode-toggle">
          <button
            className={`mode-btn ${activeMode === 'camera' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('camera')}
            id="mode-btn-camera"
          >
            <Camera size={20} className="mode-icon-svg" />
            <span className="mode-label">Camera Scan</span>
            <span className="mode-desc">Scan hard copy directly</span>
          </button>
          <button
            className={`mode-btn ${activeMode === 'scan' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('scan')}
            id="mode-btn-scan"
          >
            <Image size={20} className="mode-icon-svg" />
            <span className="mode-label">Upload Image</span>
            <span className="mode-desc">Upload bill photo</span>
          </button>
          <button
            className={`mode-btn ${activeMode === 'pdf' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('pdf')}
            id="mode-btn-pdf"
          >
            <FileText size={20} className="mode-icon-svg" />
            <span className="mode-label">Upload PDF</span>
            <span className="mode-desc">Digital PDF bill</span>
          </button>
        </div>

        {/* Camera Mode */}
        {activeMode === 'camera' && (
          <div className="camera-section">
            {!cameraActive && !capturedImage && (
              <div className="camera-start-zone">
                <div className="camera-icon-large"><Camera size={32} /></div>
                <h3 className="camera-title">Scan Your Bill</h3>
                <p className="camera-hint">
                  Place your electricity bill, fuel invoice, or gas bill in front of the camera.
                  Make sure the text is clearly visible and well-lit.
                </p>
                <button className="btn btn-primary camera-start-btn" onClick={startCamera} id="btn-start-camera">
                  Open Camera
                </button>
                {cameraError && (
                  <div className="scanner-error camera-error-msg">
                    <span className="error-icon">!</span>
                    <span>{cameraError}</span>
                  </div>
                )}
              </div>
            )}

            {cameraActive && !capturedImage && (
              <div className="camera-live-zone">
                <div className="video-container">
                  <video ref={videoRef} autoPlay playsInline muted className="camera-video" id="camera-video" />
                  <div className="camera-overlay">
                    <div className="scan-frame">
                      <div className="corner tl"></div>
                      <div className="corner tr"></div>
                      <div className="corner bl"></div>
                      <div className="corner br"></div>
                    </div>
                    <p className="scan-guide-text">Align bill within the frame</p>
                  </div>
                </div>
                <div className="camera-controls">
                  <button className="cam-ctrl-btn" onClick={toggleCamera} title="Switch Camera">
                    <RotateCcw size={18} />
                  </button>
                  <button className="cam-capture-btn" onClick={captureFrame} id="btn-capture" title="Capture">
                    <div className="capture-ring">
                      <div className="capture-dot"></div>
                    </div>
                  </button>
                  <button className="cam-ctrl-btn" onClick={stopCamera} title="Close Camera">
                    <X size={18} />
                  </button>
                </div>
              </div>
            )}

            {capturedImage && (
              <div className="captured-preview">
                <div className="captured-image-wrap">
                  <img src={capturedImage} alt="Captured bill" className="captured-image" />
                  <div className="captured-badge">Photo Captured</div>
                </div>
                <button className="btn btn-ghost retake-btn" onClick={retakePhoto}>
                  <Camera size={14} /> Retake Photo
                </button>
              </div>
            )}

            <canvas ref={canvasRef} style={{ display: 'none' }} />
          </div>
        )}

        {/* Upload Zone */}
        {(activeMode === 'scan' || activeMode === 'pdf') && (
          <div
            className={`upload-zone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !file && fileInputRef.current?.click()}
            id="upload-zone"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={acceptTypes[activeMode]}
              onChange={handleFileSelect}
              className="file-input-hidden"
              id="file-input"
            />

            {!file ? (
              <div className="upload-prompt">
                <div className="upload-icon-circle">
                  {activeMode === 'scan' ? <Image size={24} /> : <FileText size={24} />}
                </div>
                <p className="upload-title">
                  {activeMode === 'scan' ? 'Drop your bill image here' : 'Drop your PDF bill here'}
                </p>
                <p className="upload-hint">
                  or <span className="upload-browse">browse files</span>
                </p>
                <p className="upload-formats">
                  {activeMode === 'scan'
                    ? 'Supports: JPEG, PNG, WebP, BMP, TIFF · Max 10 MB'
                    : 'Supports: PDF (digital or scanned) · Max 10 MB'}
                </p>
              </div>
            ) : (
              <div className="file-preview">
                {preview ? (
                  <div className="image-preview-wrap">
                    <img src={preview} alt="Bill preview" className="image-preview" />
                    <div className="preview-overlay">
                      <span className="preview-ready">Ready to process</span>
                    </div>
                  </div>
                ) : (
                  <div className="pdf-preview">
                    <div className="pdf-icon-wrap"><FileText size={28} /></div>
                    <div className="pdf-info">
                      <p className="pdf-name">{file.name}</p>
                      <p className="pdf-size">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Pipeline Info */}
        <div className="pipeline-info">
          {activeMode === 'camera' ? (
            <div className="pipeline-steps">
              <span className="pip-step">Camera</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">OCR / Vision</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Groq AI</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Structured Data</span>
            </div>
          ) : activeMode === 'scan' ? (
            <div className="pipeline-steps">
              <span className="pip-step">Image</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Tesseract OCR</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Groq AI</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Structured Data</span>
            </div>
          ) : (
            <div className="pipeline-steps">
              <span className="pip-step">PDF</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Text Extract</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">OCR Fallback</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Groq AI</span>
              <ArrowRight size={12} className="pip-arrow-icon" />
              <span className="pip-step">Structured Data</span>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="scanner-error" id="scanner-error">
            <span className="error-icon">!</span>
            <span>{error}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="scanner-actions">
          {(file || capturedImage) && (
            <button className="btn btn-ghost" onClick={handleClear} id="btn-clear">
              Clear
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!canSubmit || loading}
            id="btn-process"
          >
            {loading ? (
              <>
                <span className="btn-spinner"></span>
                {activeMode === 'camera' ? 'Scanning…' : activeMode === 'scan' ? 'Scanning…' : 'Parsing PDF…'}
              </>
            ) : (
              <>
                <Search size={16} />
                {activeMode === 'camera' ? 'Scan & Extract' : activeMode === 'scan' ? 'Scan & Extract' : 'Parse PDF'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default BillScanner
