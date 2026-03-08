import { createNoise2D } from "https://cdn.jsdelivr.net/npm/simplex-noise@4.0.3/+esm";

const canvas = document.getElementById("game-canvas");
const splash = document.getElementById("splash-screen");
const startBtn = document.getElementById("start-btn");
const hud = document.getElementById("hud");
const optionsPanel = document.getElementById("options-panel");
const closeOptionsBtn = document.getElementById("options-close-btn");

const coordsEl = document.getElementById("coords");
const speedEl = document.getElementById("speed-display");
const fpsEl = document.getElementById("fps-display");
const compassEl = document.getElementById("compass");

const minimap = document.getElementById("minimap");
const minimapCtx = minimap.getContext("2d");

const optRenderDistance = document.getElementById("opt-render-distance");
const optTime = document.getElementById("opt-time");
const optFog = document.getElementById("opt-fog");
const optSpeed = document.getElementById("opt-speed");
const optSensitivity = document.getElementById("opt-sensitivity");
const optSaucers = document.getElementById("opt-saucers");
const optShadows = document.getElementById("opt-shadows");
const optClouds = document.getElementById("opt-clouds");

const valueLabels = {
    "opt-render-distance": document.getElementById("opt-render-distance-val"),
    "opt-time": document.getElementById("opt-time-val"),
    "opt-fog": document.getElementById("opt-fog-val"),
    "opt-speed": document.getElementById("opt-speed-val"),
    "opt-sensitivity": document.getElementById("opt-sensitivity-val"),
    "opt-saucers": document.getElementById("opt-saucers-val")
};

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x7cb9ff);
scene.fog = new THREE.Fog(0x7cb9ff, 140, 450);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1200);
camera.position.set(0, 42, 80);

scene.add(new THREE.AmbientLight(0x9ec6ff, 0.5));
const sun = new THREE.DirectionalLight(0xffffff, 1.2);
sun.position.set(120, 180, 60);
sun.castShadow = true;
sun.shadow.camera.left = -250;
sun.shadow.camera.right = 250;
sun.shadow.camera.top = 250;
sun.shadow.camera.bottom = -250;
scene.add(sun);

const cloudLayer = new THREE.Group();
scene.add(cloudLayer);
const cloudGeo = new THREE.SphereGeometry(6, 8, 8);
const cloudMat = new THREE.MeshStandardMaterial({ color: 0xf8fbff, transparent: true, opacity: 0.75 });
for (let i = 0; i < 24; i += 1) {
    const cloud = new THREE.Mesh(cloudGeo, cloudMat);
    cloud.position.set((Math.random() - 0.5) * 900, 90 + Math.random() * 30, (Math.random() - 0.5) * 900);
    cloud.scale.set(1 + Math.random() * 3, 0.5 + Math.random(), 1 + Math.random() * 3);
    cloudLayer.add(cloud);
}

const terrainGroup = new THREE.Group();
scene.add(terrainGroup);
const noise2D = createNoise2D(Math.random);
const chunkSize = 16;
const chunks = new Map();

function terrainHeight(wx, wz) {
    const a = noise2D(wx * 0.02, wz * 0.02) * 9;
    const b = noise2D(wx * 0.008, wz * 0.008) * 20;
    return Math.floor(18 + a + b);
}

function createChunk(cx, cz) {
    const key = `${cx},${cz}`;
    if (chunks.has(key)) return;
    const chunk = new THREE.Group();

    for (let x = 0; x < chunkSize; x += 1) {
        for (let z = 0; z < chunkSize; z += 1) {
            const wx = cx * chunkSize + x;
            const wz = cz * chunkSize + z;
            const h = terrainHeight(wx, wz);
            const color = h > 27 ? 0xc7d8a5 : h > 20 ? 0x72a85f : 0x4f8f55;
            const col = new THREE.Color(color).multiplyScalar(0.8 + Math.random() * 0.25);

            const column = new THREE.Mesh(
                new THREE.BoxGeometry(1, h, 1),
                new THREE.MeshLambertMaterial({ color: col })
            );
            column.position.set(wx, h / 2, wz);
            column.receiveShadow = true;
            column.castShadow = h > 22;
            chunk.add(column);
        }
    }

    terrainGroup.add(chunk);
    chunks.set(key, chunk);
}

function updateChunks(renderDistance) {
    const cx = Math.floor(camera.position.x / chunkSize);
    const cz = Math.floor(camera.position.z / chunkSize);
    const keep = new Set();

    for (let x = cx - renderDistance; x <= cx + renderDistance; x += 1) {
        for (let z = cz - renderDistance; z <= cz + renderDistance; z += 1) {
            const key = `${x},${z}`;
            keep.add(key);
            createChunk(x, z);
        }
    }

    for (const [key, chunk] of chunks.entries()) {
        if (!keep.has(key)) {
            terrainGroup.remove(chunk);
            chunk.traverse((obj) => {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) obj.material.dispose();
            });
            chunks.delete(key);
        }
    }
}

const saucerGroup = new THREE.Group();
scene.add(saucerGroup);
function createSaucer() {
    const saucer = new THREE.Group();
    const hull = new THREE.Mesh(
        new THREE.CylinderGeometry(0.2, 4, 1, 16),
        new THREE.MeshStandardMaterial({ color: 0xc5d4ef, metalness: 0.85, roughness: 0.25 })
    );
    const dome = new THREE.Mesh(
        new THREE.SphereGeometry(1.3, 14, 10),
        new THREE.MeshStandardMaterial({ color: 0x7de5ff, emissive: 0x14445a, transparent: true, opacity: 0.85 })
    );
    dome.position.y = 0.8;
    saucer.add(hull, dome);
    saucer.userData = {
        drift: Math.random() * Math.PI * 2,
        speed: 0.3 + Math.random() * 0.6,
        lift: 0.2 + Math.random() * 0.35
    };
    saucer.position.set((Math.random() - 0.5) * 300, 45 + Math.random() * 30, (Math.random() - 0.5) * 300);
    saucerGroup.add(saucer);
}

function syncSaucers(count) {
    while (saucerGroup.children.length < count) createSaucer();
    while (saucerGroup.children.length > count) saucerGroup.remove(saucerGroup.children.at(-1));
}

const state = {
    started: false,
    menuOpen: false,
    pointerLocked: false,
    yaw: 0,
    pitch: -0.2,
    moveSpeed: 1,
    sensitivity: 1,
    keys: {},
    fpsTick: performance.now(),
    frames: 0
};

function setValueLabels() {
    valueLabels["opt-render-distance"].textContent = optRenderDistance.value;
    valueLabels["opt-time"].textContent = `${Math.floor(optTime.value).toString().padStart(2, "0")}:${Number(optTime.value) % 1 ? "30" : "00"}`;
    valueLabels["opt-fog"].textContent = `${optFog.value}%`;
    valueLabels["opt-speed"].textContent = `${Number(optSpeed.value).toFixed(1)}x`;
    valueLabels["opt-sensitivity"].textContent = Number(optSensitivity.value).toFixed(1);
    valueLabels["opt-saucers"].textContent = optSaucers.value;
}

function headingFromYaw(yaw) {
    const d = ((-THREE.MathUtils.radToDeg(yaw) % 360) + 360) % 360;
    const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return dirs[Math.round(d / 45) % dirs.length];
}

function updateEnvironmentFromTime() {
    const t = Number(optTime.value);
    const angle = ((t / 24) * Math.PI * 2) - Math.PI / 2;
    const sunlight = Math.max(0.08, Math.sin(angle) * 0.9 + 0.12);
    sun.position.set(Math.cos(angle) * 180, Math.max(20, sunlight * 220), Math.sin(angle) * 180);
    sun.intensity = 0.25 + sunlight * 1.3;
    scene.fog.color.setHSL(0.58, 0.45, 0.18 + sunlight * 0.45);
    scene.background = scene.fog.color;
}

function updateFogDensity() {
    const density = Number(optFog.value) / 100;
    scene.fog.near = 60 + (1 - density) * 180;
    scene.fog.far = 190 + (1 - density) * 430;
}

function updateMinimap() {
    minimapCtx.clearRect(0, 0, minimap.width, minimap.height);
    minimapCtx.fillStyle = "#081428";
    minimapCtx.fillRect(0, 0, minimap.width, minimap.height);

    const cx = minimap.width / 2;
    const cy = minimap.height / 2;
    minimapCtx.strokeStyle = "rgba(130,180,255,0.32)";
    minimapCtx.beginPath();
    minimapCtx.arc(cx, cy, 52, 0, Math.PI * 2);
    minimapCtx.stroke();

    minimapCtx.fillStyle = "#5cff9f";
    minimapCtx.beginPath();
    minimapCtx.arc(cx, cy, 3, 0, Math.PI * 2);
    minimapCtx.fill();

    minimapCtx.strokeStyle = "#9fd0ff";
    minimapCtx.beginPath();
    minimapCtx.moveTo(cx, cy);
    minimapCtx.lineTo(cx + Math.sin(state.yaw) * 24, cy - Math.cos(state.yaw) * 24);
    minimapCtx.stroke();
}

function movePlayer(dt) {
    const forward = new THREE.Vector3(Math.sin(state.yaw), 0, -Math.cos(state.yaw));
    const right = new THREE.Vector3(forward.z, 0, -forward.x);
    const velocity = new THREE.Vector3();

    if (state.keys.KeyW) velocity.add(forward);
    if (state.keys.KeyS) velocity.sub(forward);
    if (state.keys.KeyD) velocity.add(right);
    if (state.keys.KeyA) velocity.sub(right);
    if (state.keys.Space) velocity.y += 1;
    if (state.keys.ShiftLeft || state.keys.ShiftRight) velocity.y -= 1;

    if (velocity.lengthSq() > 0) {
        velocity.normalize().multiplyScalar(34 * state.moveSpeed * dt);
        camera.position.add(velocity);
    }

    const ground = terrainHeight(camera.position.x, camera.position.z) + 6;
    if (camera.position.y < ground) camera.position.y = ground;
}

function toggleOptions(forceOpen) {
    state.menuOpen = forceOpen ?? !state.menuOpen;
    optionsPanel.classList.toggle("hidden", !state.menuOpen);
    if (state.menuOpen) {
        document.exitPointerLock();
    } else if (state.started) {
        canvas.requestPointerLock();
    }
}

startBtn.addEventListener("click", () => {
    splash.classList.add("hidden");
    hud.classList.remove("hidden");
    state.started = true;
    canvas.requestPointerLock();
});

closeOptionsBtn.addEventListener("click", () => toggleOptions(false));

window.addEventListener("keydown", (e) => {
    state.keys[e.code] = true;
    if (e.code === "Escape" && state.started) toggleOptions();
});
window.addEventListener("keyup", (e) => { state.keys[e.code] = false; });

window.addEventListener("mousemove", (e) => {
    if (!state.pointerLocked || state.menuOpen) return;
    const scale = 0.002 * state.sensitivity;
    state.yaw -= e.movementX * scale;
    state.pitch -= e.movementY * scale;
    state.pitch = THREE.MathUtils.clamp(state.pitch, -1.45, 1.45);
});

document.addEventListener("pointerlockchange", () => {
    state.pointerLocked = document.pointerLockElement === canvas;
});

[optRenderDistance, optTime, optFog, optSpeed, optSensitivity, optSaucers].forEach((el) => {
    el.addEventListener("input", () => {
        setValueLabels();
        state.moveSpeed = Number(optSpeed.value);
        state.sensitivity = Number(optSensitivity.value);
        syncSaucers(Number(optSaucers.value));
        updateEnvironmentFromTime();
        updateFogDensity();
    });
});
optShadows.addEventListener("change", () => {
    renderer.shadowMap.enabled = optShadows.checked;
});
optClouds.addEventListener("change", () => {
    cloudLayer.visible = optClouds.checked;
});

window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

function animate(now) {
    requestAnimationFrame(animate);

    const dt = Math.min(0.05, (now - state.fpsTick) / 1000);
    if (state.started && !state.menuOpen) movePlayer(dt);

    camera.rotation.order = "YXZ";
    camera.rotation.y = state.yaw;
    camera.rotation.x = state.pitch;

    updateChunks(Number(optRenderDistance.value));

    const t = now / 1000;
    saucerGroup.children.forEach((saucer, index) => {
        saucer.userData.drift += dt * saucer.userData.speed;
        saucer.position.x += Math.sin(saucer.userData.drift + index) * 0.1;
        saucer.position.z += Math.cos(saucer.userData.drift + index * 0.8) * 0.1;
        saucer.position.y += Math.sin(t * (1.5 + saucer.userData.lift)) * 0.04;
        saucer.rotation.y = saucer.userData.drift;
    });

    cloudLayer.children.forEach((cloud) => {
        cloud.position.x += 0.015;
        if (cloud.position.x > 460) cloud.position.x = -460;
    });

    coordsEl.textContent = `X: ${camera.position.x.toFixed(1)} Y: ${camera.position.y.toFixed(1)} Z: ${camera.position.z.toFixed(1)}`;
    speedEl.textContent = `Speed: ${state.moveSpeed.toFixed(1)}x`;
    compassEl.textContent = headingFromYaw(state.yaw);

    state.frames += 1;
    if (now - state.fpsTick >= 1000) {
        const fps = Math.round((state.frames * 1000) / (now - state.fpsTick));
        fpsEl.textContent = `FPS: ${fps}`;
        state.frames = 0;
        state.fpsTick = now;
    }

    updateMinimap();
    renderer.render(scene, camera);
}

setValueLabels();
syncSaucers(Number(optSaucers.value));
updateEnvironmentFromTime();
updateFogDensity();
updateChunks(Number(optRenderDistance.value));
animate(performance.now());
