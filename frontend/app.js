/**
 * Say "00" Cam - iOS Camera Application JavaScript
 * 
 * Features:
 * - Edge-to-edge camera viewfinder & Siri-style speech recognition ("Say [피사체]")
 * - "About This Project" (?) modal sheet
 * - Dual camera flip (Front/Rear camera support on mobile/desktop)
 * - Shutter button click & voice trigger dual activation
 * - Quota-safe iOS slide-up result sheet & history gallery sheet
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const webcam = document.getElementById('webcam');
  const snapshotCanvas = document.getElementById('snapshotCanvas');
  const shutterFlash = document.getElementById('shutterFlash');
  const cameraGrid = document.getElementById('cameraGrid');
  const cameraOverlay = document.getElementById('cameraOverlay');
  const btnStartCamera = document.getElementById('btnStartCamera');
  
  const btnToggleFlash = document.getElementById('btnToggleFlash');
  const btnToggleGrid = document.getElementById('btnToggleGrid');
  const btnAboutProject = document.getElementById('btnAboutProject');
  const cameraToast = document.getElementById('cameraToast');
  const toastMessage = document.getElementById('toastMessage');
  
  const triggerBanner = document.getElementById('triggerBanner');
  const detectedPhraseText = document.getElementById('detectedPhraseText');
  const siriBubble = document.getElementById('siriBubble');
  const voiceStatusText = document.getElementById('voiceStatusText');
  
  const btnShutter = document.getElementById('btnShutter');
  const btnFlipCamera = document.getElementById('btnFlipCamera');
  const btnOpenGallery = document.getElementById('btnOpenGallery');
  const galleryThumbImg = document.getElementById('galleryThumbImg');
  const galleryPlaceholderIcon = document.getElementById('galleryPlaceholderIcon');
  
  // Sheet Modal Elements
  const aboutSheet = document.getElementById('aboutSheet');
  const btnCloseAboutSheet = document.getElementById('btnCloseAboutSheet');

  const resultSheet = document.getElementById('resultSheet');
  const btnCloseResultSheet = document.getElementById('btnCloseResultSheet');
  const sheetKeywordTitle = document.getElementById('sheetKeywordTitle');
  const sheetResultReason = document.getElementById('sheetResultReason');
  const resultImgDisplay = document.getElementById('resultImgDisplay');
  const resultTypeBadge = document.getElementById('resultTypeBadge');
  const tabShowTransformed = document.getElementById('tabShowTransformed');
  const tabShowOriginal = document.getElementById('tabShowOriginal');
  const btnDownloadResult = document.getElementById('btnDownloadResult');
  const btnRetakeFromSheet = document.getElementById('btnRetakeFromSheet');
  
  const gallerySheet = document.getElementById('gallerySheet');
  const btnCloseGallerySheet = document.getElementById('btnCloseGallerySheet');
  const historyGrid = document.getElementById('historyGrid');
  const emptyGallery = document.getElementById('emptyGallery');
  const btnClearHistory = document.getElementById('btnClearHistory');

  // Application State
  let mediaStream = null;
  let currentFacingMode = 'user'; // 'user' (front) or 'environment' (rear)
  let recognition = null;
  let isListening = false;
  let lastTriggerTime = 0;
  let currentKeyword = '치즈';
  let activeResultData = null;
  let transformHistory = [];

  try {
    transformHistory = JSON.parse(localStorage.getItem('say_transform_history') || '[]');
  } catch (e) {
    transformHistory = [];
  }

  // Initialize Gallery UI & Thumbnails
  renderHistory();

  // Speech Recognition setup
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  // --------------------------------------------------------------------------
  // About This Project Sheet Modal Event Binding
  // --------------------------------------------------------------------------
  btnAboutProject.addEventListener('click', () => {
    aboutSheet.classList.add('active');
  });

  const closeAboutSheet = () => aboutSheet.classList.remove('active');
  btnCloseAboutSheet.addEventListener('click', closeAboutSheet);
  aboutSheet.addEventListener('click', (e) => {
    if (e.target === aboutSheet) closeAboutSheet();
  });

  // --------------------------------------------------------------------------
  // Camera Setup & Flip Controls
  // --------------------------------------------------------------------------
  async function startCamera(facingMode = 'user') {
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: facingMode },
        audio: false
      });
      webcam.srcObject = mediaStream;
      currentFacingMode = facingMode;
      cameraOverlay.style.display = 'none';

      // Start Siri voice recognition
      if (SpeechRecognition) {
        initSpeechRecognition();
      } else {
        voiceStatusText.textContent = '음성 인식을 지원하지 않는 브라우저입니다.';
      }
    } catch (err) {
      console.error('Camera access error:', err);
      showToast('카메라 접근 권한이 필요합니다.');
    }
  }

  btnStartCamera.addEventListener('click', () => startCamera('user'));

  btnFlipCamera.addEventListener('click', () => {
    const nextMode = currentFacingMode === 'user' ? 'environment' : 'user';
    startCamera(nextMode);
  });

  btnToggleGrid.addEventListener('click', () => {
    btnToggleGrid.classList.toggle('active');
    cameraGrid.classList.toggle('active');
  });

  btnToggleFlash.addEventListener('click', () => {
    btnToggleFlash.classList.toggle('active');
    showToast(btnToggleFlash.classList.contains('active') ? '플래시 효과 켜짐' : '플래시 효과 끔');
  });

  // --------------------------------------------------------------------------
  // Siri Voice Recognition ("Say [피사체]")
  // --------------------------------------------------------------------------
  function initSpeechRecognition() {
    if (recognition) return;

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'ko-KR';

    recognition.onstart = () => {
      isListening = true;
      document.body.classList.add('listening');
      voiceStatusText.textContent = 'Say "치즈", Say "스톤"이라고 말해보세요!';
    };

    recognition.onend = () => {
      if (isListening) {
        try { recognition.start(); } catch (e) {}
      } else {
        document.body.classList.remove('listening');
        voiceStatusText.textContent = '음성 인식 일시정지됨';
      }
    };

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const speechResult = event.results[i];
        const transcript = speechResult[0].transcript.trim();

        if (!speechResult.isFinal) {
          voiceStatusText.textContent = `듣고 있는 중: "${transcript}"`;
          continue;
        }

        console.log('Final speech result:', transcript);
        // Supports both spaced ("세이 치즈") and attached ("세이치즈", "saycheese", "새이캔디") continuous speech
        const match = transcript.match(/(?:say|세이|새이)\s*([가-힣a-zA-Z0-9]+)/i);
        if (match && match[1]) {
          const detectedKeyword = match[1].trim();

          // Ignore if the extracted keyword is empty or identical to trigger words
          if (!detectedKeyword || ['say', '세이', '새이'].includes(detectedKeyword.toLowerCase())) {
            continue;
          }

          const now = Date.now();
          if (now - lastTriggerTime < 2500) {
            console.log('Cooldown active, skipping trigger:', detectedKeyword);
            break;
          }
          lastTriggerTime = now;

          handleVoiceTrigger(detectedKeyword, transcript);
          break;
        }
      }
    };

    recognition.onerror = (e) => console.warn('Speech error:', e.error);
    recognition.start();
  }

  function handleVoiceTrigger(keyword, fullPhrase) {
    currentKeyword = keyword;

    // Show Trigger Banner Toast
    detectedPhraseText.textContent = `Say "${keyword}" 감지 완료!`;
    triggerBanner.classList.add('banner-show');
    setTimeout(() => triggerBanner.classList.remove('banner-show'), 3000);

    playShutterSound();
    snapWebcamAndTransform(keyword);
  }

  // Shutter button toggle mic & manual snap
  btnShutter.addEventListener('click', () => {
    if (!mediaStream) {
      startCamera();
      return;
    }
    
    playShutterSound();
    snapWebcamAndTransform(currentKeyword);
  });

  // --------------------------------------------------------------------------
  // Frame Capture & Audio Shutter Cue
  // --------------------------------------------------------------------------
  function captureWebcamFrame() {
    if (!mediaStream) return null;
    snapshotCanvas.width = webcam.videoWidth || 640;
    snapshotCanvas.height = webcam.videoHeight || 480;
    const ctx = snapshotCanvas.getContext('2d');
    ctx.drawImage(webcam, 0, 0, snapshotCanvas.width, snapshotCanvas.height);

    // Flash animation
    shutterFlash.classList.add('flash-active');
    setTimeout(() => shutterFlash.classList.remove('flash-active'), 200);

    return snapshotCanvas.toDataURL('image/jpeg', 0.9);
  }

  function playShutterSound() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(800, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(300, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.1);
    } catch (e) {}
  }

  // --------------------------------------------------------------------------
  // ADK 2.0 Graph API Transform Call
  // --------------------------------------------------------------------------
  async function snapWebcamAndTransform(targetKeyword) {
    const frameB64 = captureWebcamFrame();
    if (!frameB64) return;

    voiceStatusText.textContent = `"${targetKeyword}" 변환 처리 중...`;

    try {
      const response = await fetch('/api/transform', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_b64: frameB64,
          target_keyword: targetKeyword
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || '변환 처리 중 오류가 발생했습니다.');
      }

      if (!data.is_safe || !data.success) {
        showToast(data.reason || '부적절한 키워드로 차단되었습니다.');
        return;
      }

      // Successful Transformation
      displayResultSheet(data);
      saveToHistory(data);

    } catch (err) {
      console.error('Transform error:', err);
      showToast('변환 실패: ' + err.message);
    } finally {
      if (isListening) {
        voiceStatusText.textContent = 'Say "치즈", Say "스톤"이라고 말해보세요!';
      }
    }
  }

  function showToast(msg) {
    toastMessage.textContent = msg;
    cameraToast.classList.add('show');
    setTimeout(() => cameraToast.classList.remove('show'), 3500);
  }

  // --------------------------------------------------------------------------
  // iOS Slide-Up Result Sheet Modal
  // --------------------------------------------------------------------------
  function displayResultSheet(data) {
    activeResultData = data;
    sheetKeywordTitle.textContent = `Say "${data.target_keyword}"`;
    sheetResultReason.textContent = data.reason;

    // Default view transformed image
    showTransformedTab();
    btnDownloadResult.href = data.transformed_image;

    resultSheet.classList.add('active');
  }

  function showTransformedTab() {
    if (!activeResultData) return;
    tabShowTransformed.classList.add('active');
    tabShowOriginal.classList.remove('active');
    resultImgDisplay.src = activeResultData.transformed_image;
    resultTypeBadge.textContent = 'Transformed (AI)';
  }

  function showOriginalTab() {
    if (!activeResultData) return;
    tabShowOriginal.classList.add('active');
    tabShowTransformed.classList.remove('active');
    resultImgDisplay.src = activeResultData.original_image;
    resultTypeBadge.textContent = 'Original Photo';
  }

  tabShowTransformed.addEventListener('click', showTransformedTab);
  tabShowOriginal.addEventListener('click', showOriginalTab);

  const closeResultSheet = () => resultSheet.classList.remove('active');
  btnCloseResultSheet.addEventListener('click', closeResultSheet);
  btnRetakeFromSheet.addEventListener('click', closeResultSheet);
  resultSheet.addEventListener('click', (e) => {
    if (e.target === resultSheet) closeResultSheet();
  });

  // --------------------------------------------------------------------------
  // iOS History Gallery Sheet & Quota Safe Storage
  // --------------------------------------------------------------------------
  btnOpenGallery.addEventListener('click', () => {
    gallerySheet.classList.add('active');
  });

  const closeGallerySheet = () => gallerySheet.classList.remove('active');
  btnCloseGallerySheet.addEventListener('click', closeGallerySheet);
  gallerySheet.addEventListener('click', (e) => {
    if (e.target === gallerySheet) closeGallerySheet();
  });

  function createThumbnail(base64Url, maxDim = 280) {
    return new Promise((resolve) => {
      if (!base64Url) return resolve(base64Url);
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let w = img.width;
        let h = img.height;
        if (w > h) {
          if (w > maxDim) { h = Math.round((h * maxDim) / w); w = maxDim; }
        } else {
          if (h > maxDim) { w = Math.round((w * maxDim) / h); h = maxDim; }
        }
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', 0.65));
      };
      img.onerror = () => resolve(base64Url);
      img.src = base64Url;
    });
  }

  async function saveToHistory(data) {
    try {
      const thumbOriginal = await createThumbnail(data.original_image, 280);
      const thumbTransformed = await createThumbnail(data.transformed_image, 280);

      transformHistory.unshift({
        id: Date.now(),
        keyword: data.target_keyword,
        original: thumbOriginal,
        transformed: thumbTransformed,
        fullTransformed: data.transformed_image,
        fullOriginal: data.original_image,
        timestamp: new Date().toLocaleTimeString()
      });

      if (transformHistory.length > 6) transformHistory.pop();

      try {
        localStorage.setItem('say_transform_history', JSON.stringify(transformHistory));
      } catch (quotaErr) {
        transformHistory = transformHistory.slice(0, 2);
        try {
          localStorage.setItem('say_transform_history', JSON.stringify(transformHistory));
        } catch (e) {}
      }
      renderHistory();
    } catch (err) {
      console.warn('History save error:', err);
    }
  }

  function renderHistory() {
    if (transformHistory.length === 0) {
      emptyGallery.style.display = 'block';
      historyGrid.querySelectorAll('.gallery-item').forEach(el => el.remove());
      galleryThumbImg.style.display = 'none';
      galleryPlaceholderIcon.style.display = 'block';
      return;
    }

    emptyGallery.style.display = 'none';
    historyGrid.querySelectorAll('.gallery-item').forEach(el => el.remove());

    const latest = transformHistory[0];
    galleryThumbImg.src = latest.transformed;
    galleryThumbImg.style.display = 'block';
    galleryPlaceholderIcon.style.display = 'none';

    transformHistory.forEach(item => {
      const card = document.createElement('div');
      card.className = 'gallery-item';
      card.innerHTML = `
        <img src="${item.transformed}" alt="Say ${item.keyword}">
        <span class="gallery-item-tag">Say "${item.keyword}"</span>
      `;
      card.addEventListener('click', () => {
        closeGallerySheet();
        displayResultSheet({
          target_keyword: item.keyword,
          original_image: item.fullOriginal || item.original,
          transformed_image: item.fullTransformed || item.transformed,
          reason: `히스토리 항목 (${item.timestamp})`
        });
      });
      historyGrid.appendChild(card);
    });
  }

  btnClearHistory.addEventListener('click', () => {
    if (confirm('변환 히스토리를 모두 삭제하시겠습니까?')) {
      transformHistory = [];
      localStorage.removeItem('say_transform_history');
      renderHistory();
    }
  });
});
