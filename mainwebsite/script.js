document.addEventListener('DOMContentLoaded', () => {

  // ─── FAQ ACCORDION TOGGLING ───
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    question.addEventListener('click', () => {
      // Toggle current item
      const isActive = item.classList.contains('active');
      
      // Close all items
      faqItems.forEach(el => el.classList.remove('active'));
      
      // If it wasn't active, open it
      if (!isActive) {
        item.classList.add('active');
      }
    });
  });

  // ─── MEDIA PLAYER TAB TOGGLING ───
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-target');
      
      // Toggle button states
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      // Toggle content visibility
      tabContents.forEach(c => {
        if (c.getAttribute('id') === target) {
          c.classList.remove('hidden');
        } else {
          c.classList.add('hidden');
        }
      });
    });
  });

  // ─── INTERACTIVE SANDBOX UPLOAD & PROCESSING ───
  const fileSelectBtn = document.getElementById('file-select-btn');
  const dropZoneDefault = document.getElementById('drop-zone-default');
  const dropZoneFile = document.getElementById('drop-zone-file');
  const uploadedFilename = document.getElementById('uploaded-filename');
  const uploadedFilesize = document.getElementById('uploaded-filesize');
  
  const sampleChips = document.querySelectorAll('.sample-chip');
  const resetUploadBtn = document.getElementById('reset-upload-btn');
  const processDocBtn = document.getElementById('process-doc-btn');
  
  const stateIdle = document.getElementById('state-idle');
  const stateProcessing = document.getElementById('state-processing');
  const statePlayer = document.getElementById('state-player');
  
  const loaderStatus = document.getElementById('loader-status');
  const loaderDetail = document.getElementById('loader-detail');
  const progressFill = document.getElementById('progress-fill');
  
  const avatarMouth = document.getElementById('avatar-mouth');
  const playPauseBtn = document.getElementById('play-pause-btn');
  const timelinePlayed = document.getElementById('timeline-played');
  const videoTimer = document.getElementById('video-timer');
  
  let currentFile = null;
  let uploadSize = null;
  let processingInterval = null;
  let playerInterval = null;
  let isPlaying = false;
  let currentPlayTime = 0;
  const totalVideoDuration = 160; // 2 minutes 40 seconds

  // Preset chips trigger upload
  sampleChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const file = chip.getAttribute('data-file');
      const size = chip.getAttribute('data-size');
      selectFile(file, size);
    });
  });

  // Choose file button triggers upload
  fileSelectBtn.addEventListener('click', () => {
    // Simulate selecting standard syllabus
    selectFile('Syllabus_Physics_101.pdf', '2.4 MB');
  });

  function selectFile(filename, size) {
    currentFile = filename;
    uploadSize = size;
    uploadedFilename.textContent = filename;
    uploadedFilesize.textContent = `${size} • Ready to Process`;
    
    // Switch dropzone states
    dropZoneDefault.classList.add('hidden');
    dropZoneFile.classList.remove('hidden');
    
    // Reset output panels to idle
    resetOutputStates();
  }

  // Remove File click
  resetUploadBtn.addEventListener('click', () => {
    currentFile = null;
    uploadSize = null;
    
    // Switch back dropzone states
    dropZoneDefault.classList.remove('hidden');
    dropZoneFile.classList.add('hidden');
    
    // Reset outputs
    resetOutputStates();
  });

  function resetOutputStates() {
    clearInterval(processingInterval);
    clearInterval(playerInterval);
    isPlaying = false;
    currentPlayTime = 0;
    
    // Reset output views
    stateIdle.classList.remove('hidden');
    stateProcessing.classList.add('hidden');
    statePlayer.classList.add('hidden');
    
    // Reset timeline/avatar controls
    avatarMouth.classList.remove('speaking');
    playPauseBtn.textContent = '▶';
    timelinePlayed.style.width = '0%';
    videoTimer.textContent = '0:00 / 2:40';
  }

  // Process Document / Generate now click trigger
  processDocBtn.addEventListener('click', () => {
    if (!currentFile) return;
    
    // Start processing state transition
    stateIdle.classList.add('hidden');
    stateProcessing.classList.remove('hidden');
    statePlayer.classList.add('hidden');
    
    let progress = 0;
    progressFill.style.width = '0%';
    
    // Loop mock progress updates
    processingInterval = setInterval(() => {
      progress += 2;
      progressFill.style.width = `${progress}%`;
      
      if (progress < 25) {
        loaderStatus.textContent = 'Uploading Document...';
        loaderDetail.textContent = 'Parsing document tags and extracting raw text headings...';
      } else if (progress < 50) {
        loaderStatus.textContent = 'Analyzing Syllabus Structure...';
        loaderDetail.textContent = 'Structuring learning module sections and defining goals...';
      } else if (progress < 75) {
        loaderStatus.textContent = 'Generating Voice & Avatar...';
        loaderDetail.textContent = 'Synthesizing script speech audio and syncing visual expressions...';
      } else if (progress < 95) {
        loaderStatus.textContent = 'Creating Quizzes & Worksheets...';
        loaderDetail.textContent = 'Designing pop-up checks, pre-objectives, and post-question metrics...';
      } else {
        loaderStatus.textContent = 'Finalizing Video Assembly...';
        loaderDetail.textContent = 'Rendering lecture file and syncing timeline triggers...';
      }
      
      if (progress >= 100) {
        clearInterval(processingInterval);
        launchVideoPlayer();
      }
    }, 80);
  });

  // Launch Video player once processed
  function launchVideoPlayer() {
    stateProcessing.classList.add('hidden');
    statePlayer.classList.remove('hidden');
    
    isPlaying = true;
    playPauseBtn.textContent = '⏸';
    avatarMouth.classList.add('speaking');
    
    currentPlayTime = 0;
    
    // Start simulated playback clock
    playerInterval = setInterval(() => {
      if (isPlaying) {
        currentPlayTime++;
        
        // Calculate played timeline fill
        const percentage = (currentPlayTime / totalVideoDuration) * 100;
        timelinePlayed.style.width = `${percentage}%`;
        
        // Format time string
        const pad = (num) => String(num).padStart(2, '0');
        const minutes = Math.floor(currentPlayTime / 60);
        const seconds = currentPlayTime % 60;
        videoTimer.textContent = `${minutes}:${pad(seconds)} / 2:40`;
        
        // Randomize mouth movement simulation (simulating syllables)
        if (currentPlayTime % 3 === 0) {
          avatarMouth.style.animationDuration = `${0.2 + Math.random() * 0.3}s`;
        }
        
        if (currentPlayTime >= totalVideoDuration) {
          isPlaying = false;
          playPauseBtn.textContent = '▶';
          avatarMouth.classList.remove('speaking');
          clearInterval(playerInterval);
        }
      }
    }, 1000);
  }

  // Play/Pause button trigger
  playPauseBtn.addEventListener('click', () => {
    if (!currentFile || statePlayer.classList.contains('hidden')) return;
    
    isPlaying = !isPlaying;
    if (isPlaying) {
      playPauseBtn.textContent = '⏸';
      avatarMouth.classList.add('speaking');
    } else {
      playPauseBtn.textContent = '▶';
      avatarMouth.classList.remove('speaking');
    }
  });

  // ─── MOBILE RESPONSIVE HAMBURGER MENU ───
  const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
  const navMenu = document.querySelector('.nav-menu');
  
  mobileMenuToggle.addEventListener('click', () => {
    navMenu.classList.toggle('mobile-active');
  });

});
