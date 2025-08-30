document.addEventListener('DOMContentLoaded', () => {
    // --- Element References ---
    const galleryContainer = document.getElementById('gallery-container');
    const lightbox = document.getElementById('lightbox');
    const lightboxMediaWrapper = lightbox.querySelector('.media-wrapper');
    const lightboxClose = lightbox.querySelector('.lightbox-close');
    const lightboxDownload = lightbox.querySelector('.lightbox-download');
    const prevButton = lightbox.querySelector('.lightbox-nav.prev');
    const nextButton = lightbox.querySelector('.lightbox-nav.next');
    const filenameDisplay = lightbox.querySelector('.filename');
    const metadataDisplay = lightbox.querySelector('.metadata');

    // --- State Variables ---
    let currentItems = [];
    let currentIndex = -1;
    let isAnimating = false;

    let totalZoom = 0;
    let isMouseDown = false;
    let translateX = 0;
    let translateY = 0;
    let lastMouseX = 0;
    let lastMouseY = 0;

    let enableSwipe = true;
    const swipeThreshold = 70;
    let lastTouchX = 0;
    let lastTouchY = 0;
    let touchStartX = 0;
    let touchEndX = 0;
    let initialDistance = null;
    let currentDistance = null;

    // let newMedia;
    let mediaWidth;
    let mediaHeight;

    // Mouse
    window.addEventListener('mousedown', function(event) {
        isMouseDown = true;
        lastMouseX = event.clientX;
        lastMouseY = event.clientY;
    });
    window.addEventListener('mouseup', function(event) {
        isMouseDown = false;
    });
    
    // Touch

    function getDistance(touches) {
        const [touch1, touch2] = touches;
        return Math.hypot(
            touch2.pageX - touch1.pageX,
            touch2.pageY - touch1.pageY
        );
    }
    window.addEventListener('touchstart', function(event) {
        touchStartX = event.changedTouches[0].screenX;
        if (event.touches.length === 2) {
            initialDistance = getDistance(event.touches);
        } else if (event.touches.length === 1) {
            lastTouchX = event.touches[0].clientX;
            lastTouchY = event.touches[0].clientY;
        }
    });

    window.addEventListener('touchend', function(event) {
        touchEndX = event.changedTouches[0].screenX;
        if (event.touches.length === 1) {
            lastTouchX = event.touches[0].clientX;
            lastTouchY = event.touches[0].clientY;
        }
        if (enableSwipe) handleSwipe();
    });



    // --- Gallery Loading and Rendering ---
    async function fetchAndRenderGallery() {
        try {
            const response = await fetch('/api/gallery-data');
            const data = await response.json();
            
            galleryContainer.innerHTML = '';
            if (data.error || !data.structure || data.structure.length === 0) {
                 galleryContainer.innerHTML = `<p style="text-align: center;">No media folders were found.</p>`;
                 return;
            }
            const fragment = document.createDocumentFragment();
            data.structure.forEach(item => fragment.appendChild(createAccordionItem(item)));
            galleryContainer.appendChild(fragment);
        } catch (error) {
            galleryContainer.innerHTML = '<p style="text-align: center;">An error occured with server comunication.</p>';
        }
    }

    function createAccordionItem(folderItem) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'accordion-item';

        const headerDiv = document.createElement('div');
        headerDiv.className = 'accordion-header';
        headerDiv.innerHTML = `<h2>${folderItem.name}</h2><div class="header-controls"><a href="/download/section/${folderItem.path}" class="section-download" title="Download section"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg></a><span class="accordion-toggle">&#10095;</span></div>`;

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'accordion-content-wrapper';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'accordion-content';
        contentWrapper.appendChild(contentDiv);
        
        itemDiv.append(headerDiv, contentWrapper);

        headerDiv.onclick = (e) => {
            e.stopPropagation();
            toggleAccordion(itemDiv, folderItem);
        };
        return itemDiv;
    }

    function toggleAccordion(itemDiv, folderItem) {
        if (itemDiv.classList.contains('active')) {
            closeAccordion(itemDiv);
        } else {
            const parentEl = itemDiv.parentElement.closest('.accordion-content') || galleryContainer;
            parentEl.querySelectorAll(':scope > .accordion-item.active').forEach(active => closeAccordion(active));
            openAccordion(itemDiv, folderItem);
        }
    }

    function openAccordion(itemDiv, folderItem) {
        itemDiv.classList.add('active');
        const contentDiv = itemDiv.querySelector('.accordion-content');
        if (!contentDiv.innerHTML) {
            const mediaItems = folderItem.children.filter(c => c.type === 'image' || c.type === 'video');
            const subFolders = folderItem.children.filter(c => c.type === 'folder');
            
            subFolders.forEach(child => contentDiv.appendChild(createAccordionItem(child)));

            if (mediaItems.length > 0) {
                const grid = document.createElement('div');
                grid.className = 'thumbnail-grid';
                mediaItems.forEach(media => grid.appendChild(createThumbnail(media, mediaItems)));
                contentDiv.appendChild(grid);
            }
        }
        setTimeout(() => itemDiv.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }
    
    function closeAccordion(itemDiv) {
        itemDiv.classList.remove('active');
    }

    function createThumbnail(media, allItems) {
        const thumbItem = document.createElement('div');
        thumbItem.className = 'thumbnail-item';
        thumbItem.innerHTML = `<img src="/thumbnail/${media.path}" alt="Preview of ${media.name}" loading="lazy">`;

        if (media.type === 'video') {
            thumbItem.innerHTML += `<div class="video-overlay"><svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><polygon points="30,20 80,50 30,80" fill="white"/></svg></div>`;
        }
        thumbItem.onclick = () => initLightbox(allItems, allItems.indexOf(media));
        return thumbItem;
    }

    // --- Lightbox Logic ---
    function initLightbox(items, index) {
        currentItems = items;
        currentIndex = index;
        lightbox.classList.add('show');
        document.addEventListener('keydown', handleKeyPress);
        document.querySelector("body").style.overflow = "hidden";
        renderLightboxMedia();
    }

    function renderLightboxMedia() {
        window.removeEventListener('wheel', handleScroll);
        window.removeEventListener('mousemove', handleMove);
        window.removeEventListener('touchmove', handleTouchMove);
        translateX = 0;
        translateY = 0;
        totalZoom = 0;
        lastMouseX = 0;
        lastMouseY = 0;
        lastTouchX = 0;
        lastTouchY = 0;
        updateNavButtons()

        if (currentIndex < 0 || currentIndex >= currentItems.length) return;
        isAnimating = true;
        const item = currentItems[currentIndex];


        lightboxMediaWrapper.innerHTML = '<div class="loader"></div>';
        newMedia = item.type === 'video' ? document.createElement('video') : document.createElement('img');
        newMedia.style.opacity = '0';
        newMedia.style.display = 'none';

        if (item.type === 'video') {
            newMedia.src = `/media/${item.path}`;
            newMedia.controls = true; newMedia.autoplay = true;
        } else {
            newMedia.src = `/media/${item.path}`; newMedia.alt = item.name;
        }

        newMedia.onload = newMedia.oncanplay = () => {
            lightboxMediaWrapper.querySelector("div.loader").style.display = "none";
            setTimeout(() => {
                newMedia.style.display = "block";
            }, 20)
            setTimeout(() => {
                newMedia.style.opacity = '1';
                isAnimating = false;
                mediaWidth = newMedia.clientWidth
                mediaHeight = newMedia.clientHeight
            }, 50)
        };

        lightboxMediaWrapper.appendChild(newMedia);
        filenameDisplay.textContent = item.name;
        metadataDisplay.textContent = item.metadata.created;
        lightboxDownload.href = `/media/${item.path}`;
        lightboxDownload.download = item.name;
        updateNavButtons();

        window.addEventListener('wheel', handleScroll);
        window.addEventListener('mousemove', handleMove);
        window.addEventListener("touchmove", handleTouchMove);
    }
    
    function closeLightbox() {
        if (newMedia.tagName === "VIDEO") newMedia.pause();
        lightbox.classList.remove('show');
        window.removeEventListener('wheel', handleScroll);
        window.removeEventListener('mousemove', handleMove);
        window.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('keydown', handleKeyPress);
        document.querySelector("body").style.overflow = "auto";
    }

    function showNext() {
        if (isAnimating || currentIndex >= currentItems.length - 1) return;
        currentIndex++;
        renderLightboxMedia();
    }
    function showPrev() {
        if (isAnimating || currentIndex <= 0) return;
        currentIndex--;
        renderLightboxMedia();
    }

    function updateNavButtons() {
        prevButton.classList.toggle('hidden', currentIndex === 0);
        nextButton.classList.toggle('hidden', currentIndex === currentItems.length - 1);
    }

    function handleKeyPress(e) {
        if (e.key === 'Escape') closeLightbox();
        if (e.key === 'ArrowRight') showNext();
        if (e.key === 'ArrowLeft') showPrev();
    }

    // Zoom and move
    function handleScroll(event) {
        enableSwipe = false;
        if (event.type == 'touchmove') {
            totalZoom += (currentDistance - initialDistance) / 200;
            initialDistance = currentDistance;
            newMedia.style.transition = "opacity 0.2s ease-in-out"
        } else {
            totalZoom += -1 * event.deltaY / 200;
            newMedia.style.transition = "opacity 0.2s ease-in-out, scale 0.2s ease"
        }
        totalZoom = Math.max(0, Math.min(5, totalZoom)); // clamp zoom 0–5
        newMedia.style.scale = 2 ** totalZoom;

        if (totalZoom == 0) {
            updateNavButtons()
            if (newMedia.tagName === "VIDEO") {
                newMedia.setAttribute('controls', true);
            }
            newMedia.style.cursor = "unset";
            newMedia.style.transition = "opacity 0.2s ease-in-out, scale 0.1s ease, transform 0.2s ease";
            setTimeout(() => {
                newMedia.style.transform = "translate(0, 0)";
            }, 20)
            setTimeout(() => {
                newMedia.style.transition = "opacity 0.2s ease-in-out, scale 0.2s ease"
            }, 220)
            translateX = 0;
            translateY = 0;


        } else {
            newMedia.style.cursor = "move";
            if (newMedia.tagName === "VIDEO") {
                newMedia.removeAttribute('controls');
            }
            prevButton.classList.add('hidden');
            nextButton.classList.add('hidden');
        }
    }
    function handleMove(event) {
        if (isMouseDown && totalZoom != 0) {
            let deltaX = (event.clientX - lastMouseX) / (2 ** totalZoom);
            let deltaY = (event.clientY - lastMouseY) / (2 ** totalZoom);
            if ((translateX + deltaX < mediaWidth/2) && (mediaWidth/2*-1 < translateX + deltaX)) translateX += deltaX;
            if ((translateY + deltaY < mediaHeight/2) && (mediaHeight/2*-1 < translateY + deltaY)) translateY += deltaY;
                
            lastMouseX = event.clientX;
            lastMouseY = event.clientY;

            newMedia.style.transform = `translate(${translateX}px, ${translateY}px)`;
        } else if (event.type == 'touchmove' && totalZoom != 0) {
            let deltaX = (event.touches[0].clientX - lastTouchX) / (2 ** totalZoom);
            let deltaY = (event.touches[0].clientY - lastTouchY) / (2 ** totalZoom);
            if ((translateX + deltaX < mediaWidth/2) && (mediaWidth/2*-1 < translateX + deltaX)) translateX += deltaX;
            if ((translateY + deltaY < mediaHeight/2) && (mediaHeight/2*-1 < translateY + deltaY)) translateY += deltaY;
                
            lastTouchX = event.touches[0].clientX;
            lastTouchY = event.touches[0].clientY;

            newMedia.style.transform = `translate(${translateX}px, ${translateY}px)`;
        }
    }
    function handleTouchMove(event) {
        if (event.touches.length === 2 && initialDistance !== null) {
            currentDistance = getDistance(event.touches);
            handleScroll(event);
        } else if (event.touches.length === 1) {
            handleMove(event);
            setTimeout(() => {
                enableSwipe = true;
            }, 500);
        }
    }

    // Swipe
    function handleSwipe() {
        if (lightbox.classList.contains("show") && totalZoom === 0) {
            if (touchEndX < touchStartX - swipeThreshold && currentIndex !== currentItems.length - 1) {
                 newMedia.style.transition = "opacity 0.2s ease-in-out, scale 0.1s ease, transform 0.2s ease";
                setTimeout(() => {
                    newMedia.style.transform = `translate(${-window.innerWidth}px, 0)`;
                }, 20);
                setTimeout(() => {
                    showNext();
                    newMedia.style.transition = "opacity 0.2s ease-in-out, scale 0.2s ease"
                }, 220);
            } else if (touchEndX > touchStartX + swipeThreshold && currentIndex !== 0) {
                newMedia.style.transition = "opacity 0.2s ease-in-out, scale 0.1s ease, transform 0.2s ease";
                setTimeout(() => {
                    newMedia.style.transform = `translate(${window.innerWidth}px, 0)`;
                }, 20);
                setTimeout(() => {
                    showPrev();
                    newMedia.style.transition = "opacity 0.2s ease-in-out, scale 0.2s ease"
                }, 220);
            }
        }
    }

    lightboxClose.addEventListener('click', closeLightbox);
    prevButton.addEventListener('click', showPrev);
    nextButton.addEventListener('click', showNext);

    
    fetchAndRenderGallery();

    // Nastavit pozadí podle skupiny
    let bgName = document.getElementById("bg-file").value;
    if (bgName) document.querySelector("body").style.backgroundImage = "url(static/" + bgName + ")";

});