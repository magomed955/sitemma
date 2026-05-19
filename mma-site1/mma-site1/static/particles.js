const canvas = document.getElementById("particles-canvas");
const ctx = canvas.getContext("2d");

let w = canvas.width = window.innerWidth;
let h = canvas.height = window.innerHeight;

window.addEventListener("resize", () => {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
});

let mouse = { x: w / 2, y: h / 2 };

window.addEventListener("mousemove", (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
});

const particles = [];
const COUNT = 50;

class Particle {
    constructor() {
        this.x = Math.random() * w;
        this.y = Math.random() * h;
        this.vx = (Math.random() - 0.5) * 0.6;
        this.vy = (Math.random() - 0.5) * 0.6;
        this.r = Math.random() * 2 + 1;
        this.baseX = this.x;
        this.baseY = this.y;

        this.color = Math.random() > 0.5
            ? "rgba(232,0,13,0.9)"
            : "rgba(160,160,160,0.6)";
    }

    update() {
        // mouvement normal
        this.x += this.vx;
        this.y += this.vy;

        if (this.x < 0 || this.x > w) this.vx *= -1;
        if (this.y < 0 || this.y > h) this.vy *= -1;

        // attraction souris (effet "aimant UFC")
        let dx = mouse.x - this.x;
        let dy = mouse.y - this.y;
        let dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 120) {
            this.x -= dx * 0.02;
            this.y -= dy * 0.02;
        }
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.shadowBlur = 12;
        ctx.shadowColor = this.color;
        ctx.fill();
    }
}

for (let i = 0; i < COUNT; i++) {
    particles.push(new Particle());
}

function connect() {
    for (let i = 0; i < particles.length; i++) {
        for (let j = i; j < particles.length; j++) {

            let dx = particles[i].x - particles[j].x;
            let dy = particles[i].y - particles[j].y;

            let dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < 140) {
                ctx.beginPath();
                ctx.strokeStyle = `rgba(232,0,13,${1 - dist / 140})`;
                ctx.lineWidth = 0.6;

                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.stroke();
            }
        }
    }
}

function animate() {
    ctx.clearRect(0, 0, w, h);

    particles.forEach(p => {
        p.update();
        p.draw();
    });

    connect();

    requestAnimationFrame(animate);
}

animate();

const flash = document.createElement("div");

flash.style.position = "fixed";
flash.style.inset = "0";
flash.style.background = "rgba(232,0,13,0.6)";
flash.style.zIndex = "99999";
flash.style.pointerEvents = "none";
flash.style.opacity = "1";

document.body.appendChild(flash);

// animation contrôlée
setTimeout(() => {
    flash.style.transition = "opacity 0.8s ease-out";
    flash.style.opacity = "0";
}, 100);

setTimeout(() => {
    flash.remove();
}, 1000);