/**
 * Say "00" Cam - iOS Camera Application JavaScript
 * 
 * Features:
 * - Edge-to-edge camera viewfinder & Siri-style speech recognition ("Say [피사체]")
 * - Quota Management (Default 10 Free Shots) with Firestore Client Tracking
 * - Blob-based Reliable Image Download & iOS Native Web Share API ("Album Save")
 * - Lemon Squeezy Paywall Modal Integration
 * - Firestore NoSQL History Gallery Integration
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
  const quotaCount = document.getElementById('quotaCount');
  
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
  const btnShareResult = document.getElementById('btnShareResult');
  const btnRetakeFromSheet = document.getElementById('btnRetakeFromSheet');
  
  const gallerySheet = document.getElementById('gallerySheet');
  const btnCloseGallerySheet = document.getElementById('btnCloseGallerySheet');
  const historyGrid = document.getElementById('historyGrid');
  const emptyGallery = document.getElementById('emptyGallery');
  const btnClearHistory = document.getElementById('btnClearHistory');

  // Paywall & Google Auth Sheet Elements
  const googleAuthSheet = document.getElementById('googleAuthSheet');
  const btnCloseGoogleAuthSheet = document.getElementById('btnCloseGoogleAuthSheet');
  const btnGoogleLogin = document.getElementById('btnGoogleLogin');
  const btnOpenPaywallFromAuth = document.getElementById('btnOpenPaywallFromAuth');

  const paywallSheet = document.getElementById('paywallSheet');
  const btnClosePaywallSheet = document.getElementById('btnClosePaywallSheet');
  const btnBuy5Shots = document.getElementById('btnBuy5Shots');
  const btnBuy20Shots = document.getElementById('btnBuy20Shots');

  // Application State
  let mediaStream = null;
  let currentFacingMode = 'user'; // 'user' or 'environment'
  let recognition = null;
  let isListening = false;
  let lastTriggerTime = 0;
  let currentKeyword = '치즈';
  let activeResultData = null;
  let transformHistory = [];
  let userQuota = { free_shots: 10, paid_shots: 0, total_remaining: 10 };

  // Generate or retrieve persistent Client UUID
  function getClientId() {
    let cid = localStorage.getItem('say_client_id');
    if (!cid) {
      cid = 'client_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
      localStorage.setItem('say_client_id', cid);
    }
    return cid;
  }
  const clientId = getClientId();

  // Fetch initial User Quota from Backend
  fetchUserQuota();

  async function fetchUserQuota() {
    try {
      const res = await fetch(`/api/user/quota?client_id=${clientId}`);
      if (res.ok) {
        const data = await res.json();
        userQuota = data;
        updateQuotaDisplay(data.total_remaining);
      }
    } catch (e) {
      console.warn('Quota fetch error:', e);
    }
  }

  function updateQuotaDisplay(remaining) {
    if (quotaCount) {
      quotaCount.textContent = remaining;
    }
  }

  // Load history from Firestore / LocalStorage fallback
  fetchHistoryFromServer();

  // Speech Recognition setup
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  // --------------------------------------------------------------------------
  // About & Paywall Sheet Modal Event Bindings
  // --------------------------------------------------------------------------
  btnAboutProject.addEventListener('click', () => aboutSheet.classList.add('active'));
  const closeAboutSheet = () => aboutSheet.classList.remove('active');
  btnCloseAboutSheet.addEventListener('click', closeAboutSheet);
  aboutSheet.addEventListener('click', (e) => { if (e.target === aboutSheet) closeAboutSheet(); });

  const closeGoogleAuthSheet = () => googleAuthSheet.classList.remove('active');
  if (btnCloseGoogleAuthSheet) btnCloseGoogleAuthSheet.addEventListener('click', closeGoogleAuthSheet);
  if (googleAuthSheet) googleAuthSheet.addEventListener('click', (e) => { if (e.target === googleAuthSheet) closeGoogleAuthSheet(); });

  if (btnOpenPaywallFromAuth) {
    btnOpenPaywallFromAuth.addEventListener('click', () => {
      closeGoogleAuthSheet();
      paywallSheet.classList.add('active');
    });
  }

  // Firebase Auth Setup for Google Sign-In
  let auth = null;
  function initFirebaseAuth() {
    if (window.firebase && !firebase.apps.length) {
      const firebaseConfig = {
        apiKey: "AIzaSyCFB6BAX1Wle8f_q3-duSSGFs1-nxs_H8A",
        authDomain: "mommocmoc-say-00.firebaseapp.com",
        projectId: "mommocmoc-say-00"
      };
      try {
        firebase.initializeApp(firebaseConfig);
        auth = firebase.auth();
      } catch (e) {
        console.warn('Firebase Auth init warn:', e);
      }
    }
  }
  initFirebaseAuth();

  // Google 1-second Login Handler (Upgrades 3-shot guest to 10-shot member)
  if (btnGoogleLogin) {
    btnGoogleLogin.addEventListener('click', async () => {
      try {
        showToast('Google 계정 로그인 팝업 호출 중...');
        let googleUserPayload = null;

        if (window.firebase && firebase.auth) {
          const provider = new firebase.auth.GoogleAuthProvider();
          provider.addScope('email');
          provider.addScope('profile');
          const result = await firebase.auth().signInWithPopup(provider);
          googleUserPayload = {
            google_uid: result.user.uid,
            email: result.user.email || 'user@gmail.com',
            name: result.user.displayName || 'SayCam User',
            anon_client_id: clientId
          };
        } else {
          // Fallback simulation for local dev without domain registration
          googleUserPayload = {
            google_uid: 'user_' + Date.now().toString().slice(-6),
            email: 'user' + Math.floor(Math.random()*1000) + '@gmail.com',
            name: 'SayCam User',
            anon_client_id: clientId
          };
        }

        const res = await fetch('/api/user/google-login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(googleUserPayload)
        });

        if (res.ok) {
          const data = await res.json();
          localStorage.setItem('say_client_id', data.user_id);
          userQuota = data.quota;
          updateQuotaDisplay(data.quota.total_remaining);
          closeGoogleAuthSheet();
          showToast(`🎉 Google 로그인 완료! 7회 추가 지급으로 총 ${data.quota.total_remaining}회 촬영이 가능합니다.`);
          fetchHistoryFromServer();
        } else {
          showToast('Google 로그인 처리 실패');
        }
      } catch (e) {
        console.warn('Google login error:', e);
        if (e.code === 'auth/popup-closed-by-user') {
          showToast('Google 로그인 팝업이 닫혔습니다.');
        } else {
          showToast('Google 로그인 팝업 호출 오류: ' + (e.message || '인증 불가'));
        }
      }
    });
  }

  const closePaywallSheet = () => paywallSheet.classList.remove('active');
  btnClosePaywallSheet.addEventListener('click', closePaywallSheet);
  paywallSheet.addEventListener('click', (e) => { if (e.target === paywallSheet) closePaywallSheet(); });

  btnBuy5Shots.addEventListener('click', () => {
    showToast('Lemon Squeezy 결제 연동 예정입니다. (테스트용 +5회 충전 완료)');
    userQuota.total_remaining += 5;
    updateQuotaDisplay(userQuota.total_remaining);
    closePaywallSheet();
  });

  btnBuy20Shots.addEventListener('click', () => {
    showToast('Lemon Squeezy 결제 연동 예정입니다. (테스트용 +20회 충전 완료)');
    userQuota.total_remaining += 20;
    updateQuotaDisplay(userQuota.total_remaining);
    closePaywallSheet();
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

    detectedPhraseText.textContent = `Say "${keyword}" 감지 완료!`;
    triggerBanner.classList.add('banner-show');
    setTimeout(() => triggerBanner.classList.remove('banner-show'), 3000);

    playShutterSound();
    snapWebcamAndTransform(keyword);
  }

  btnShutter.addEventListener('click', () => {
    if (!mediaStream) {
      startCamera();
      return;
    }
    
    playShutterSound();
    snapWebcamAndTransform(currentKeyword);
  });

  // --------------------------------------------------------------------------
  // Frame Capture & Audio Cue
  // --------------------------------------------------------------------------
  function captureWebcamFrame() {
    if (!mediaStream) return null;
    snapshotCanvas.width = webcam.videoWidth || 640;
    snapshotCanvas.height = webcam.videoHeight || 480;
    const ctx = snapshotCanvas.getContext('2d');
    ctx.drawImage(webcam, 0, 0, snapshotCanvas.width, snapshotCanvas.height);

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
  // ADK 2.0 Graph API Transform Call with Quota check
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
          target_keyword: targetKeyword,
          client_id: clientId
        })
      });

      const data = await response.json();

      if (response.status === 402) {
        if (!userQuota.is_google_user && !clientId.startsWith('google_')) {
          googleAuthSheet.classList.add('active');
          showToast('비회원 3회 맛보기 촬영이 소진되었습니다. 구글 로그인 시 7회 추가!');
        } else {
          paywallSheet.classList.add('active');
          showToast('무료 촬영권을 소진하셨습니다. 레몬스퀴지로 추가 충전하세요.');
        }
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || '변환 처리 중 오류가 발생했습니다.');
      }

      if (!data.is_safe || !data.success) {
        showToast(data.reason || '부적절한 키워드로 차단되었습니다.');
        return;
      }

      // Update remaining quota display
      if (typeof data.remaining_shots === 'number') {
        updateQuotaDisplay(data.remaining_shots);
      }

      // Display Result & Save History
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
  // iOS Slide-Up Result Sheet Modal with Mobile Reliable Download & Native Share
  // --------------------------------------------------------------------------
  function displayResultSheet(data) {
    activeResultData = data;
    sheetKeywordTitle.textContent = `Say "${data.target_keyword}"`;
    sheetResultReason.textContent = data.reason;

    showTransformedTab();
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

  // Reliable Blob-based Image Download for iOS / Mobile Safari
  btnDownloadResult.addEventListener('click', async () => {
    if (!activeResultData) return;
    const imgUrl = activeResultData.transformed_image || activeResultData.original_image;
    const filename = `say_${activeResultData.target_keyword || 'photo'}_${Date.now()}.jpg`;

    try {
      showToast('사진 다운로드 준비 중...');
      const response = await fetch(imgUrl);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      showToast('사진이 성공적으로 저장되었습니다!');
    } catch (e) {
      console.warn('Blob download error:', e);
      window.open(imgUrl, '_blank');
    }
  });

  // Mobile Native Web Share API (Album Direct Save on iOS/Android)
  btnShareResult.addEventListener('click', async () => {
    if (!activeResultData) return;
    const imgUrl = activeResultData.transformed_image || activeResultData.original_image;
    const filename = `say_${activeResultData.target_keyword || 'photo'}.jpg`;

    try {
      const response = await fetch(imgUrl);
      const blob = await response.blob();
      const file = new File([blob], filename, { type: 'image/jpeg' });

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          title: `Say "${activeResultData.target_keyword}" AI 사진`,
          text: `Say "00" Cam으로 생성한 '${activeResultData.target_keyword}' 변환 사진입니다!`,
          files: [file]
        });
        showToast('공유/사진 앱 저장 성공!');
      } else {
        // Fallback for desktop or unsupported browsers
        btnDownloadResult.click();
      }
    } catch (e) {
      console.warn('Share API error:', e);
      btnDownloadResult.click();
    }
  });

  const closeResultSheet = () => resultSheet.classList.remove('active');
  btnCloseResultSheet.addEventListener('click', closeResultSheet);
  btnRetakeFromSheet.addEventListener('click', closeResultSheet);
  resultSheet.addEventListener('click', (e) => {
    if (e.target === resultSheet) closeResultSheet();
  });

  // --------------------------------------------------------------------------
  // iOS History Gallery Sheet (Firestore Server & Local Storage)
  // --------------------------------------------------------------------------
  btnOpenGallery.addEventListener('click', () => {
    fetchHistoryFromServer();
    gallerySheet.classList.add('active');
  });

  const closeGallerySheet = () => gallerySheet.classList.remove('active');
  btnCloseGallerySheet.addEventListener('click', closeGallerySheet);
  gallerySheet.addEventListener('click', (e) => {
    if (e.target === gallerySheet) closeGallerySheet();
  });

  async function fetchHistoryFromServer() {
    try {
      const res = await fetch(`/api/history?client_id=${clientId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.history && data.history.length > 0) {
          transformHistory = data.history.map(item => ({
            id: item.record_id,
            keyword: item.target_keyword,
            transformed: item.transformed_image,
            original: item.original_image,
            fullTransformed: item.transformed_image,
            fullOriginal: item.original_image,
            timestamp: new Date(item.timestamp * 1000).toLocaleTimeString()
          }));
          renderHistory();
          return;
        }
      }
    } catch (e) {
      console.warn('Firestore history fetch error, fallback to LocalStorage:', e);
    }

    try {
      transformHistory = JSON.parse(localStorage.getItem('say_transform_history') || '[]');
      renderHistory();
    } catch (e) {
      transformHistory = [];
    }
  }

  function saveToHistory(data) {
    transformHistory.unshift({
      id: Date.now(),
      keyword: data.target_keyword,
      transformed: data.transformed_image,
      original: data.original_image,
      fullTransformed: data.transformed_image,
      fullOriginal: data.original_image,
      timestamp: new Date().toLocaleTimeString()
    });

    if (transformHistory.length > 20) transformHistory.pop();

    try {
      localStorage.setItem('say_transform_history', JSON.stringify(transformHistory));
    } catch (e) {}

    renderHistory();
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
    if (confirm('변환 히스토리를 삭제하시겠습니까?')) {
      transformHistory = [];
      localStorage.removeItem('say_transform_history');
      renderHistory();
    }
  });
});
