/**
 * AURA — Unified Voice Intelligence Frontend
 * Pure Voice-to-Voice across all 3 modes:
 * 1. General Voice Bot
 * 2. PDF Knowledge Base Agent
 * 3. Real-Time Web Research Agent
 */

document.addEventListener('DOMContentLoaded', () => {
  const API = window.location.origin;

  // ─── State ───
  let activeTab = 'voice'; // 'voice' | 'pdf' | 'web'
  let isConnected = false;
  let pc = null;
  let dc = null;
  let micStream = null;
  let audioCtx = null;
  let analyser = null;
  let speaking = false;
  let currentBubble = null;
  let history = [];
  let visualizer = null;
  let lastUserQuery = '';

  // ─── DOM refs ───
  const $ = id => document.getElementById(id);

  // Navigation
  const navVoice = $('navVoice');
  const navPdf   = $('navPdf');
  const navWeb   = $('navWeb');
  const navBtns  = [navVoice, navPdf, navWeb].filter(Boolean);

  // Header
  const stageTitle       = $('stageTitle');
  const stageSubtitle    = $('stageSubtitle');
  const modeBadgeText    = $('modeBadgeText');
  const vizModes         = $('vizModes');
  const docsToggleBtn    = $('docsToggleBtn');
  const docsBtnCount     = $('docsBtnCount');
  const sourcesToggleBtn = $('sourcesToggleBtn');
  const sourcesBtnCount  = $('sourcesBtnCount');
  const transcriptToggle = $('transcriptToggle');

  // Stage & Voice
  const caption   = $('caption');
  const orbBtn    = $('orbBtn');
  const orbLabel  = $('orbLabel');
  const hintChips = $('hintChips');
  const vizCanvas = $('vizCanvas');
  const remoteAudio = $('remoteAudio');

  // Drawers
  const transcriptDrawer   = $('transcriptDrawer');
  const closeTranscript    = $('closeTranscript');
  const clearTranscript    = $('clearTranscript');
  const voiceFeed          = $('voiceFeed');

  const docsDrawer         = $('docsDrawer');
  const closeDocsDrawer    = $('closeDocsDrawer');
  const docsDrawerBadge    = $('docsDrawerBadge');
  const dropZone           = $('dropZone');
  const fileInput          = $('fileInput');
  const uploadProgress     = $('uploadProgress');
  const uploadMsg          = $('uploadMsg');
  const docList            = $('docList');
  const docBadge           = $('docBadge');
  const refreshDocs        = $('refreshDocs');

  const sourcesDrawer      = $('sourcesDrawer');
  const closeSourcesDrawer = $('closeSourcesDrawer');
  const sourcesDrawerBadge = $('sourcesDrawerBadge');
  const webSrcTitle        = $('webSrcTitle');
  const webSrcLabel        = $('webSrcLabel');
  const webLoading         = $('webLoading');
  const webGrid            = $('webGrid');

  // Sidebar Footer
  const memTurns  = $('memTurns');
  const memClear  = $('memClear');
  const statusDot = $('statusDot');
  const statusText = $('statusText');
  const themeBtn  = $('themeBtn');
  const themeIco  = $('themeIco');

  // ─────────────────────────────────────────────
  // MODE CONFIGURATIONS
  // ─────────────────────────────────────────────
  const MODE_CONFIG = {
    voice: {
      backendMode: 'general',
      badge: 'General AI',
      title: 'Voice Assistant',
      subtitle: 'Speak naturally in English, Hindi, or Hinglish — Aura listens and replies with voice',
      orbLabel: 'Start Talking',
      hints: [
        '"Python kya hai?"',
        '"What is quantum computing?"',
        '"Explain recursion simply"',
        '"Tell me a fun science fact"'
      ]
    },
    pdf: {
      backendMode: 'rag',
      badge: 'PDF Knowledge Active',
      title: 'Document Voice Agent',
      subtitle: 'Voice-to-voice Q&A strictly grounded in your uploaded PDF knowledge base',
      orbLabel: 'Ask Document',
      hints: [
        '"Summarize this document"',
        '"What are the key conclusions?"',
        '"List important dates and figures"',
        '"Explain the main methodology"'
      ]
    },
    web: {
      backendMode: 'web',
      badge: 'Live Web Research Active',
      title: 'News & Web Voice Agent',
      subtitle: 'Ask about current events, breaking news, or market updates — Aura searches the live web and replies by voice',
      orbLabel: 'Ask Live News',
      hints: [
        '"Latest AI breakthroughs today"',
        '"Stock market headlines"',
        '"Top world news today"',
        '"What is the latest weather forecast?"'
      ]
    }
  };

  // ─────────────────────────────────────────────
  // STARFIELD BACKGROUND
  // ─────────────────────────────────────────────
  const bgCanvas = $('bgCanvas');
  const bgCtx = bgCanvas.getContext('2d');
  let stars = [];

  function initStars() {
    bgCanvas.width = window.innerWidth;
    bgCanvas.height = window.innerHeight;
    stars = [];
    const count = Math.floor((bgCanvas.width * bgCanvas.height) / 9000);
    for (let i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * bgCanvas.width,
        y: Math.random() * bgCanvas.height,
        r: Math.random() * 1.1,
        a: Math.random(),
        speed: 0.0015 + Math.random() * 0.0025,
        dir: Math.random() > 0.5 ? 1 : -1,
      });
    }
  }

  function animateStars() {
    bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    stars.forEach(s => {
      s.a += s.speed * s.dir;
      if (s.a > 1 || s.a < 0) s.dir *= -1;
      bgCtx.beginPath();
      bgCtx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      bgCtx.fillStyle = isDark
        ? `rgba(148,168,255,${s.a * 0.55})`
        : `rgba(60,90,200,${s.a * 0.2})`;
      bgCtx.fill();
    });
    requestAnimationFrame(animateStars);
  }

  initStars();
  animateStars();
  window.addEventListener('resize', initStars);

  // ─────────────────────────────────────────────
  // VISUALIZER ENGINE
  // ─────────────────────────────────────────────
  if (vizCanvas && typeof VisualizerEngine !== 'undefined') {
    visualizer = new VisualizerEngine(vizCanvas);
    visualizer.start();
  }

  if (vizModes) {
    vizModes.querySelectorAll('.viz-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        vizModes.querySelectorAll('.viz-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        if (visualizer) visualizer.setMode(btn.getAttribute('data-mode'));
      });
    });
  }

  // ─────────────────────────────────────────────
  // THEME TOGGLE
  // ─────────────────────────────────────────────
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('aura_theme', theme);
    if (themeIco) {
      themeIco.innerHTML = theme === 'light'
        ? `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`
        : `<circle cx="12" cy="12" r="5"/>
           <line x1="12" y1="1" x2="12" y2="3"/>
           <line x1="12" y1="21" x2="12" y2="23"/>
           <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
           <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
           <line x1="1" y1="12" x2="3" y2="12"/>
           <line x1="21" y1="12" x2="23" y2="12"/>
           <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
           <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>`;
    }
  }
  applyTheme(localStorage.getItem('aura_theme') || 'dark');
  themeBtn?.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  });

  // ─────────────────────────────────────────────
  // TAB SWITCHING (Unified Experience)
  // ─────────────────────────────────────────────
  function switchTab(tab) {
    if (!MODE_CONFIG[tab]) return;
    activeTab = tab;
    const cfg = MODE_CONFIG[tab];

    // 1. Sidebar Nav
    navBtns.forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-tab') === tab);
    });

    // 2. Stage Header
    if (stageTitle) stageTitle.textContent = cfg.title;
    if (stageSubtitle) stageSubtitle.textContent = cfg.subtitle;
    if (modeBadgeText) modeBadgeText.textContent = cfg.badge;

    // 3. Header Controls Visibility
    if (vizModes) vizModes.style.display = (tab === 'voice') ? 'flex' : 'none';
    if (docsToggleBtn) docsToggleBtn.classList.toggle('hidden', tab !== 'pdf');
    if (sourcesToggleBtn) sourcesToggleBtn.classList.toggle('hidden', tab !== 'web');

    // 4. Orb Label
    if (orbLabel) {
      orbLabel.textContent = isConnected ? 'End Session' : cfg.orbLabel;
    }

    // 5. Hint Chips
    if (hintChips) {
      hintChips.innerHTML = cfg.hints.map(h => `<span class="hint-chip">${h}</span>`).join('');
    }

    // 6. Sync backend mode via DataChannel
    if (dc && dc.readyState === 'open') {
      dc.send(JSON.stringify({ type: 'set_mode', mode: cfg.backendMode }));
    }

    // Auto-load docs on PDF tab
    if (tab === 'pdf') loadDocs();

    // Auto-open PDF drawer if in PDF tab and 0 docs exist
    if (tab === 'pdf' && docBadge && docBadge.textContent === '0') {
      closeAllDrawers();
      docsDrawer?.classList.remove('hidden');
    }

    if (visualizer) {
      setTimeout(() => visualizer.resize(), 50);
    }
  }

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
  });

  // ─────────────────────────────────────────────
  // DRAWER HELPERS
  // ─────────────────────────────────────────────
  function closeAllDrawers() {
    transcriptDrawer?.classList.add('hidden');
    docsDrawer?.classList.add('hidden');
    sourcesDrawer?.classList.add('hidden');
  }

  transcriptToggle?.addEventListener('click', () => {
    const isHidden = transcriptDrawer.classList.contains('hidden');
    closeAllDrawers();
    if (isHidden) transcriptDrawer.classList.remove('hidden');
  });
  closeTranscript?.addEventListener('click', () => transcriptDrawer.classList.add('hidden'));

  docsToggleBtn?.addEventListener('click', () => {
    const isHidden = docsDrawer.classList.contains('hidden');
    closeAllDrawers();
    if (isHidden) docsDrawer.classList.remove('hidden');
  });
  closeDocsDrawer?.addEventListener('click', () => docsDrawer.classList.add('hidden'));

  sourcesToggleBtn?.addEventListener('click', () => {
    const isHidden = sourcesDrawer.classList.contains('hidden');
    closeAllDrawers();
    if (isHidden) sourcesDrawer.classList.remove('hidden');
  });
  closeSourcesDrawer?.addEventListener('click', () => sourcesDrawer.classList.add('hidden'));

  // ─────────────────────────────────────────────
  // MEMORY MANAGEMENT
  // ─────────────────────────────────────────────
  function updateMemory() {
    const turns = Math.floor(history.length / 2);
    if (memTurns) memTurns.textContent = `${turns} ${turns === 1 ? 'turn' : 'turns'}`;
  }

  memClear?.addEventListener('click', () => {
    history = [];
    updateMemory();
    currentBubble = null;
    removeTypingIndicator();
    if (dc && dc.readyState === 'open') dc.send(JSON.stringify({ type: 'clear_history' }));
  });

  // ─────────────────────────────────────────────
  // STATUS HELPERS
  // ─────────────────────────────────────────────
  function setStatus(text, state = 'idle') {
    if (caption) caption.textContent = text;
    if (statusDot) {
      statusDot.className = 'status-dot';
      if (state === 'online')         statusDot.classList.add('online');
      else if (state === 'listening') statusDot.classList.add('listening');
      else if (state === 'speaking')  statusDot.classList.add('speaking');
    }
    if (statusText) {
      statusText.textContent =
        state === 'online'    ? 'Connected'
        : state === 'listening' ? 'Listening'
        : state === 'speaking'  ? 'Speaking'
        : 'Offline';
    }
  }

  function setOrbActive(active) {
    if (!orbBtn) return;
    orbBtn.classList.toggle('active', active);
    const cfg = MODE_CONFIG[activeTab] || MODE_CONFIG.voice;
    if (orbLabel) {
      orbLabel.textContent = active ? 'End Session' : cfg.orbLabel;
    }
    orbBtn.disabled = false;
  }

  // ─────────────────────────────────────────────
  // MARKDOWN RENDERER
  // ─────────────────────────────────────────────
  function renderMd(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br/>');
  }

  // ─────────────────────────────────────────────
  // NATIVE BROWSER SPEECH RECOGNITION (Fallback)
  // ─────────────────────────────────────────────
  let speechRecognizer = null;

  function initClientSTT() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    if (speechRecognizer) return;

    speechRecognizer = new SpeechRecognition();
    speechRecognizer.continuous = true;
    speechRecognizer.interimResults = true;
    speechRecognizer.lang = 'en-IN';

    speechRecognizer.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (interimTranscript && speaking) {
        remoteAudio.muted = true;
        speaking = false;
        removeTypingIndicator();
      }
      if (interimTranscript) {
        setStatus(`Hearing: "${interimTranscript}"`, 'listening');
      }

      if (finalTranscript.trim()) {
        const text = finalTranscript.trim();
        if (dc && dc.readyState === 'open') {
          dc.send(JSON.stringify({ type: 'client_transcript', text: text }));
        }
      }
    };

    speechRecognizer.onerror = (e) => {
      console.warn('SpeechRecognition notice:', e.error);
    };

    speechRecognizer.onend = () => {
      if (isConnected) {
        try { speechRecognizer.start(); } catch (_) {}
      }
    };
  }

  function startClientSTT() {
    initClientSTT();
    if (speechRecognizer && isConnected) {
      try { speechRecognizer.start(); } catch (_) {}
    }
  }

  function stopClientSTT() {
    if (speechRecognizer) {
      try { speechRecognizer.stop(); } catch (_) {}
    }
  }
  function addBubble(container, role, text = '') {
    if (!container) return null;
    const empty = container.querySelector('.empty-feed');
    if (empty) empty.remove();

    const wrap = document.createElement('div');
    wrap.className = `bubble ${role}`;

    const roleEl = document.createElement('span');
    roleEl.className = 'bubble-role';
    roleEl.textContent = role === 'user' ? 'You' : 'Aura';
    wrap.appendChild(roleEl);

    const body = document.createElement('span');
    body.className = 'bubble-body';
    body.rawText = text;
    body.innerHTML = renderMd(text);
    wrap.appendChild(body);

    container.appendChild(wrap);
    container.scrollTop = container.scrollHeight;
    return body;
  }

  function showTypingIndicator(container) {
    if (!container) return;
    removeTypingIndicator();

    const wrap = document.createElement('div');
    wrap.className = 'bubble assistant typing-bubble';
    wrap.id = 'typingIndicator';

    const roleEl = document.createElement('span');
    roleEl.className = 'bubble-role';
    roleEl.textContent = 'Aura';
    wrap.appendChild(roleEl);

    const body = document.createElement('span');
    body.className = 'bubble-body';
    body.innerHTML = `
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>`;
    wrap.appendChild(body);

    container.appendChild(wrap);
    container.scrollTop = container.scrollHeight;
    return wrap;
  }

  function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
  }

  // ─────────────────────────────────────────────
  // WebRTC VOICE PIPELINE
  // ─────────────────────────────────────────────
  async function startSession() {
    orbBtn.disabled = true;
    if (orbLabel) orbLabel.textContent = 'Connecting…';
    setStatus('Requesting microphone…', 'idle');

    try {
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });

      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.85;
      audioCtx.createMediaStreamSource(micStream).connect(analyser);
      if (visualizer) visualizer.setAnalyser(analyser);

      pc = new RTCPeerConnection();
      micStream.getAudioTracks().forEach(t => pc.addTrack(t, micStream));

      // Control data channel
      dc = pc.createDataChannel('voice-control');
      dc.onopen = () => {
        const cfg = MODE_CONFIG[activeTab] || MODE_CONFIG.voice;
        dc.send(JSON.stringify({ type: 'set_mode', mode: cfg.backendMode }));
        setStatus('Listening…', 'listening');
        setOrbActive(true);
        startClientSTT();
      };
      dc.onmessage = e => {
        try { handleEvent(JSON.parse(e.data)); } catch (_) {}
      };

      // Remote incoming assistant voice audio
      pc.ontrack = e => {
        remoteAudio.srcObject = e.streams[0];
        remoteAudio.muted = false;
        remoteAudio.play().catch(() => {});
        try {
          const remote = audioCtx.createMediaStreamSource(e.streams[0]);
          remote.connect(analyser);
        } catch (_) {}
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'connected') {
          isConnected = true;
        } else if (['failed', 'closed', 'disconnected'].includes(pc.connectionState)) {
          stopSession();
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitICE(pc);

      const res = await fetch(`${API}/api/webrtc/offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const answer = await res.json();
      await pc.setRemoteDescription(new RTCSessionDescription(answer));

    } catch (err) {
      console.error('WebRTC start failed:', err);
      setStatus(`Error: ${err.message}`, 'idle');
      stopSession();
    }
  }

  function waitICE(peerConn) {
    if (peerConn.iceGatheringState === 'complete') return Promise.resolve();
    return new Promise(resolve => {
      const check = () => {
        if (peerConn.iceGatheringState === 'complete') {
          peerConn.removeEventListener('icegatheringstatechange', check);
          resolve();
        }
      };
      peerConn.addEventListener('icegatheringstatechange', check);
      setTimeout(resolve, 5000);
    });
  }

  function stopSession() {
    isConnected = false;
    speaking = false;
    currentBubble = null;
    removeTypingIndicator();
    stopClientSTT();

    if (dc) { try { dc.close(); } catch (_) {} dc = null; }
    if (pc) { try { pc.close(); } catch (_) {} pc = null; }
    if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
    if (visualizer) {
      try { visualizer.setAnalyser(null); } catch (_) {}
    }
    if (audioCtx) { try { audioCtx.close(); } catch (_) {} audioCtx = null; }
    analyser = null;

    setStatus('Click the orb to start speaking', 'idle');
    setOrbActive(false);
  }

  orbBtn?.addEventListener('click', () => {
    if (isConnected) stopSession();
    else startSession();
  });

  // ─────────────────────────────────────────────
  // EVENT HANDLER
  // ─────────────────────────────────────────────
  function handleEvent(ev) {
    switch (ev.type) {

      case 'enable_client_stt':
        startClientSTT();
        break;

      case 'ready':
        setStatus('Listening…', 'listening');
        break;

      case 'partial':
        // ONLY trigger user barge-in if actual speech text is present
        if (ev.text && ev.text.trim()) {
          if (speaking) {
            speaking = false;
            remoteAudio.muted = true;
            removeTypingIndicator();
          }
          setStatus(`Hearing: "${ev.text}"`, 'listening');
        }
        break;

      case 'search_status':
        setStatus(ev.text || 'Searching live web…', 'listening');
        break;

      case 'transcript': {
        addBubble(voiceFeed, 'user', ev.text);
        lastUserQuery = ev.text;
        history.push({ role: 'user', content: ev.text });
        updateMemory();

        if (activeTab === 'web') {
          setStatus('Searching live web…', 'listening');
          if (webSrcTitle) webSrcTitle.textContent = `Query: "${ev.text}"`;
          if (webSrcLabel) webSrcLabel.textContent = 'Searching Serper API…';
        } else if (activeTab === 'pdf') {
          setStatus('Searching document…', 'listening');
        } else {
          setStatus('Thinking…', 'listening');
        }

        showTypingIndicator(voiceFeed);
        break;
      }

      case 'turn_start':
        speaking = true;
        remoteAudio.muted = false;
        remoteAudio.play().catch(() => {});
        setStatus('Aura is speaking…', 'speaking');
        removeTypingIndicator();
        currentBubble = addBubble(voiceFeed, 'assistant', '');
        break;

      case 'text':
        if (ev.text && currentBubble) {
          const old = currentBubble.rawText || '';
          currentBubble.rawText = old + (old && !old.endsWith(' ') ? ' ' : '') + ev.text;
          currentBubble.innerHTML = renderMd(currentBubble.rawText);
          if (voiceFeed) voiceFeed.scrollTop = voiceFeed.scrollHeight;
        }
        break;

      case 'turn_end':
        speaking = false;
        const replyText = currentBubble?.rawText || '';
        if (replyText) {
          history.push({ role: 'assistant', content: replyText });
          updateMemory();
        }
        currentBubble = null;
        setStatus('Listening…', 'listening');

        // If in Web tab, fetch live source cards
        if (activeTab === 'web' && lastUserQuery) {
          fetchWebSources(lastUserQuery);
        }
        break;

      case 'history_updated':
        if (ev.count !== undefined && memTurns) {
          memTurns.textContent = `${ev.count} ${ev.count === 1 ? 'turn' : 'turns'}`;
        }
        break;

      case 'interrupted':
        speaking = false;
        currentBubble = null;
        remoteAudio.muted = true;
        removeTypingIndicator();
        setStatus('Listening…', 'listening');
        break;

      case 'error':
        removeTypingIndicator();
        setStatus(`Notice: ${ev.message}`, 'idle');
        break;
    }
  }

  clearTranscript?.addEventListener('click', () => {
    if (voiceFeed) {
      voiceFeed.innerHTML = `<div class="empty-feed">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="30" height="30" style="opacity:.25">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
          <path d="M19 10v1a7 7 0 0 1-14 0v-1"/>
        </svg>
        <p>Start talking — your conversation appears here</p>
      </div>`;
    }
    history = [];
    updateMemory();
    if (dc && dc.readyState === 'open') dc.send(JSON.stringify({ type: 'clear_history' }));
  });

  // ─────────────────────────────────────────────
  // PDF UPLOAD & LIBRARY
  // ─────────────────────────────────────────────
  dropZone?.addEventListener('click', () => fileInput?.click());

  dropZone?.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone?.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer?.files[0];
    if (file) uploadPDF(file);
  });

  fileInput?.addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) uploadPDF(file);
  });

  async function uploadPDF(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are accepted.');
      return;
    }
    const form = new FormData();
    form.append('file', file);

    uploadProgress.classList.remove('hidden');
    uploadMsg.textContent = `Indexing "${file.name}"…`;

    try {
      const res = await fetch(`${API}/api/documents/upload`, { method: 'POST', body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Upload failed');
      }
      const data = await res.json();
      uploadMsg.textContent = `✓ ${data.document.pages} pages · ${data.document.chunks_count} chunks indexed`;
      setTimeout(() => uploadProgress.classList.add('hidden'), 2500);
      loadDocs();
      addBubble(voiceFeed, 'assistant',
        `Indexed **${file.name}** (${data.document.pages} pages). You can now ask questions about it by voice!`);
    } catch (err) {
      uploadMsg.textContent = `Error: ${err.message}`;
      setTimeout(() => uploadProgress.classList.add('hidden'), 3000);
    } finally {
      if (fileInput) fileInput.value = '';
    }
  }

  async function loadDocs() {
    try {
      const res = await fetch(`${API}/api/documents`);
      if (!res.ok) return;
      const data = await res.json();
      const docs = data.documents || [];
      const count = docs.length;

      if (docBadge) docBadge.textContent = count;
      if (docsBtnCount) docsBtnCount.textContent = count;
      if (docsDrawerBadge) docsDrawerBadge.textContent = `${count} ${count === 1 ? 'PDF' : 'PDFs'}`;

      if (!docList) return;
      if (count === 0) {
        docList.innerHTML = '<div class="doc-empty">No files uploaded yet. Add a PDF to start voice Q&amp;A.</div>';
        return;
      }

      docList.innerHTML = '';
      docs.forEach(doc => {
        const item = document.createElement('div');
        item.className = 'doc-item';
        item.innerHTML = `
          <span class="doc-item-icon">📄</span>
          <div class="doc-item-info">
            <span class="doc-item-name" title="${doc.filename}">${doc.filename}</span>
            <span class="doc-item-meta">${doc.pages}p · ${doc.chunks_count} chunks · ${Math.round(doc.file_size / 1024)}KB</span>
          </div>
          <button class="doc-delete-btn" data-id="${doc.doc_id}" title="Delete">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>`;

        item.querySelector('.doc-delete-btn').addEventListener('click', async e => {
          e.stopPropagation();
          if (confirm(`Remove "${doc.filename}"?`)) {
            await fetch(`${API}/api/documents/${doc.doc_id}`, { method: 'DELETE' });
            loadDocs();
          }
        });
        docList.appendChild(item);
      });
    } catch (err) {
      console.warn('loadDocs error:', err);
    }
  }

  refreshDocs?.addEventListener('click', loadDocs);

  // ─────────────────────────────────────────────
  // WEB SOURCES FETCHING
  // ─────────────────────────────────────────────
  async function fetchWebSources(query) {
    if (!webLoading || !webGrid) return;
    webLoading.classList.remove('hidden');
    webGrid.innerHTML = '';
    if (webSrcLabel) webSrcLabel.textContent = 'Fetching live sources…';

    try {
      const res = await fetch(`${API}/api/research/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, num_results: 5 })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const results = data.results || [];

      if (sourcesBtnCount) sourcesBtnCount.textContent = results.length;
      if (sourcesDrawerBadge) sourcesDrawerBadge.textContent = `${results.length} sources`;
      if (webSrcLabel) webSrcLabel.textContent = `${results.length} verified live sources found`;

      if (results.length === 0) {
        webGrid.innerHTML = '<div class="doc-empty">No external sources needed for this answer.</div>';
        return;
      }

      results.forEach(r => {
        let domain = 'Web';
        try { domain = new URL(r.link).hostname.replace('www.', ''); } catch (_) {}

        const card = document.createElement('div');
        card.className = 'src-card';
        card.innerHTML = `
          <span class="src-domain">${domain}</span>
          <a href="${r.link}" target="_blank" rel="noopener" class="src-title">${r.title || 'Untitled'}</a>
          <p class="src-snippet">${r.snippet || ''}</p>
          <a href="${r.link}" target="_blank" rel="noopener" class="src-link">
            Open article →
          </a>`;
        webGrid.appendChild(card);
      });
    } catch (err) {
      if (webSrcLabel) webSrcLabel.textContent = `Search notice: ${err.message}`;
    } finally {
      webLoading.classList.add('hidden');
    }
  }

  // ─────────────────────────────────────────────
  // AMBIENT RINGS ANIMATION
  // ─────────────────────────────────────────────
  const ring1 = $('ring1');
  const ring2 = $('ring2');

  function animateRings() {
    if (analyser && (speaking || isConnected)) {
      const arr = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(arr);
      const avg = arr.slice(0, 64).reduce((a, b) => a + b, 0) / 64;
      const scale = 1 + (avg / 255) * 0.14;
      if (ring1) ring1.style.transform = `translate(-50%, -50%) scale(${scale})`;
      if (ring2) ring2.style.transform = `translate(-50%, -50%) scale(${scale * 0.96})`;
    } else {
      if (ring1) ring1.style.transform = 'translate(-50%, -50%) scale(1)';
    }
    requestAnimationFrame(animateRings);
  }
  animateRings();

  // ─────────────────────────────────────────────
  // INITIALIZATION
  // ─────────────────────────────────────────────
  fetch(`${API}/health`)
    .then(r => r.json())
    .then(d => {
      if (d.status === 'ok') setStatus('Click the orb to start speaking', 'online');
    })
    .catch(() => setStatus('Backend offline — check server', 'idle'));

  loadDocs();
  switchTab('voice');
});
