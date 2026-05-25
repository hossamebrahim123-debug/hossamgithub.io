let currentSlide = 0;

function changeSlide(direction) {
    const slides = document.querySelectorAll('.slide');

    // Hide current slide
    slides[currentSlide].classList.remove('active');

    // Calculate next index (loops back to start if at end)
    currentSlide = (currentSlide + direction + slides.length) % slides.length;

    // Show new slide
    slides[currentSlide].classList.add('active');
}

// Auto-play: changes slide every 5 seconds
setInterval(() => {
    changeSlide(1);
}, 5000);

:root {
    --farm-green: #2e4a27;
    --farm-gold: #d4a373;
    --cream: #fefae0;
}

body {
    margin: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: var(--cream);
}

/* Slider Styling */
.hero-slider {
    position: relative;
    width: 100%;
    height: 80vh; /* Takes up 80% of screen height */
    overflow: hidden;
}

.slider-container, .slides, .slide {
    height: 100%;
    width: 100%;
}

.slide {
    display: none;
    position: relative;
}

.slide.active {
    display: block;
    animation: fade 1s ease-in-out;
}

.slide img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

/* Text Overlay */
.slide-content {
    position: absolute;
    top: 50%;
    left: 10%;
    transform: translateY(-50%);
    color: white;
    text-shadow: 2px 2px 10px rgba(0,0,0,0.5);
}

.slide-content h1 { font-size: 4rem; margin-bottom: 10px; }
.btn-farm {
    display: inline-block;
    padding: 12px 30px;
    background: var(--farm-green);
    color: white;
    text-decoration: none;
    border-radius: 5px;
    margin-top: 20px;
}

/* Arrows */
.prev, .next {
    position: absolute;
    top: 50%;
    background: rgba(0,0,0,0.2);
    color: white;
    border: none;
    padding: 20px;
    cursor: pointer;
    font-size: 2rem;
    transition: 0.3s;
}
.next { right: 0; }
.prev:hover, .next:hover { background: var(--farm-green); }

/* Features Section */
.features {
    display: flex;
    justify-content: space-around;
    padding: 50px 10%;
    text-align: center;
}

.feature-card i {
    font-size: 3rem;
    color: var(--farm-green);
    margin-bottom: 15px;
}

@keyframes fade {
    from { opacity: 0.7; }
    to { opacity: 1; }
}