#!/usr/bin/env python3
"""Voxel Skyways - standalone desktop game (pygame).

Controls:
- W/A/S/D: move
- Space / Left Ctrl: ascend / descend
- Mouse: look
- Esc: options menu
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass

import pygame


SCREEN_W = 1280
SCREEN_H = 720
SKY_COLOR = (16, 24, 44)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def hash2(x: int, y: int, seed: int) -> float:
    n = (x * 374761393 + y * 668265263 + seed * 1274126177) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return n / 0xFFFFFFFF


def value_noise(x: float, y: float, seed: int) -> float:
    x0 = math.floor(x)
    y0 = math.floor(y)
    tx = x - x0
    ty = y - y0

    v00 = hash2(x0, y0, seed)
    v10 = hash2(x0 + 1, y0, seed)
    v01 = hash2(x0, y0 + 1, seed)
    v11 = hash2(x0 + 1, y0 + 1, seed)

    sx = smoothstep(tx)
    sy = smoothstep(ty)

    ix0 = v00 + (v10 - v00) * sx
    ix1 = v01 + (v11 - v01) * sx
    return ix0 + (ix1 - ix0) * sy


def fractal_noise(x: float, y: float, seed: int) -> float:
    amplitude = 1.0
    frequency = 1.0
    total = 0.0
    norm = 0.0
    for i in range(4):
        total += value_noise(x * frequency, y * frequency, seed + i * 101) * amplitude
        norm += amplitude
        amplitude *= 0.5
        frequency *= 2.03
    return total / norm


def terrain_height(wx: float, wz: float, seed: int) -> float:
    h1 = fractal_noise(wx * 0.015, wz * 0.015, seed)
    h2 = fractal_noise(wx * 0.006, wz * 0.006, seed + 499)
    return 20.0 + h1 * 20.0 + h2 * 50.0


def terrain_color(height: float) -> tuple[int, int, int]:
    if height > 58:
        return (183, 203, 151)
    if height > 40:
        return (102, 155, 92)
    return (66, 121, 73)


@dataclass
class Saucer:
    x: float
    z: float
    y: float
    phase: float
    speed: float


class VoxelSkywaysGame:
    def __init__(self, width: int, height: int, headless: bool = False):
        self.width = width
        self.height = height
        self.headless = headless

        pygame.init()
        pygame.display.set_caption("Voxel Skyways - Desktop Edition")
        flags = pygame.SCALED | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((width, height), flags)
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("consolas", 18)
        self.title_font = pygame.font.SysFont("consolas", 46, bold=True)

        self.seed = random.randint(1, 999999)
        self.running = True
        self.started = False
        self.menu_open = False

        self.pos_x = 0.0
        self.pos_z = 0.0
        self.pos_y = 85.0
        self.yaw = 0.0
        self.pitch = 0.0

        self.render_distance = 26
        self.speed_multiplier = 1.0
        self.sensitivity = 0.2
        self.fog = 0.42
        self.time_of_day = 10.0
        self.clouds_enabled = True
        self.saucers_count = 8

        self.fps = 0
        self.saucers: list[Saucer] = []
        self._rebuild_saucers()

        self.mouse_locked = False
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

    def _rebuild_saucers(self) -> None:
        while len(self.saucers) < self.saucers_count:
            self.saucers.append(
                Saucer(
                    x=random.uniform(-280, 280),
                    z=random.uniform(-280, 280),
                    y=random.uniform(70, 120),
                    phase=random.random() * math.tau,
                    speed=random.uniform(0.35, 0.8),
                )
            )
        self.saucers = self.saucers[: self.saucers_count]

    def _set_pointer_lock(self, lock: bool) -> None:
        self.mouse_locked = lock
        pygame.event.set_grab(lock)
        pygame.mouse.set_visible(not lock)
        if lock:
            pygame.mouse.get_rel()

    def _toggle_menu(self) -> None:
        self.menu_open = not self.menu_open
        self._set_pointer_lock(self.started and not self.menu_open)

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            if self.started:
                self._toggle_menu()
            return
        if not self.menu_open:
            return
        if key == pygame.K_LEFT:
            self.render_distance = max(10, self.render_distance - 1)
        elif key == pygame.K_RIGHT:
            self.render_distance = min(45, self.render_distance + 1)
        elif key == pygame.K_UP:
            self.speed_multiplier = min(4.0, self.speed_multiplier + 0.1)
        elif key == pygame.K_DOWN:
            self.speed_multiplier = max(0.4, self.speed_multiplier - 0.1)
        elif key == pygame.K_1:
            self.time_of_day = (self.time_of_day - 1.0) % 24.0
        elif key == pygame.K_2:
            self.time_of_day = (self.time_of_day + 1.0) % 24.0
        elif key == pygame.K_3:
            self.fog = clamp(self.fog - 0.03, 0.05, 0.9)
        elif key == pygame.K_4:
            self.fog = clamp(self.fog + 0.03, 0.05, 0.9)
        elif key == pygame.K_c:
            self.clouds_enabled = not self.clouds_enabled
        elif key == pygame.K_MINUS:
            self.saucers_count = max(0, self.saucers_count - 1)
            self._rebuild_saucers()
        elif key == pygame.K_EQUALS:
            self.saucers_count = min(24, self.saucers_count + 1)
            self._rebuild_saucers()

    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if not self.started and event.key == pygame.K_RETURN:
                    self.started = True
                    self._set_pointer_lock(True)
                self._handle_keydown(event.key)

    def _update(self, dt: float) -> None:
        if not self.started or self.menu_open:
            return

        mx, my = pygame.mouse.get_rel()
        self.yaw -= mx * self.sensitivity * 0.01
        self.pitch = clamp(self.pitch - my * self.sensitivity * 0.01, -1.2, 1.2)

        keys = pygame.key.get_pressed()
        forward_x = math.sin(self.yaw)
        forward_z = -math.cos(self.yaw)
        right_x = forward_z
        right_z = -forward_x

        vx = vz = vy = 0.0
        if keys[pygame.K_w]:
            vx += forward_x
            vz += forward_z
        if keys[pygame.K_s]:
            vx -= forward_x
            vz -= forward_z
        if keys[pygame.K_d]:
            vx += right_x
            vz += right_z
        if keys[pygame.K_a]:
            vx -= right_x
            vz -= right_z
        if keys[pygame.K_SPACE]:
            vy += 1.0
        if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
            vy -= 1.0

        mag = math.sqrt(vx * vx + vz * vz + vy * vy)
        if mag > 0.0001:
            vx /= mag
            vz /= mag
            vy /= mag

        speed = 85.0 * self.speed_multiplier
        self.pos_x += vx * speed * dt
        self.pos_z += vz * speed * dt
        self.pos_y += vy * speed * dt

        min_alt = terrain_height(self.pos_x, self.pos_z, self.seed) + 9.0
        if self.pos_y < min_alt:
            self.pos_y = min_alt

        t = pygame.time.get_ticks() * 0.001
        for i, saucer in enumerate(self.saucers):
            saucer.phase += dt * saucer.speed
            saucer.x += math.sin(saucer.phase + i) * 0.25
            saucer.z += math.cos(saucer.phase + i * 0.8) * 0.25
            saucer.y += math.sin(t * (1.2 + saucer.speed)) * 0.06

    def _project(self, wx: float, wz: float, h: float) -> tuple[float, float, float] | None:
        dx = wx - self.pos_x
        dz = wz - self.pos_z

        sin_y = math.sin(-self.yaw)
        cos_y = math.cos(-self.yaw)
        rx = dx * cos_y - dz * sin_y
        rz = dx * sin_y + dz * cos_y

        if rz < 1.0:
            return None

        base_fov = 500.0
        perspective = base_fov / rz

        horizon = self.height * 0.52 + self.pitch * 120
        sy = horizon - ((h - self.pos_y) * perspective)
        sx = self.width * 0.5 + rx * perspective

        return sx, sy, perspective

    def _draw_world(self) -> None:
        t = self.time_of_day / 24.0
        sun = max(0.12, math.sin((t * math.tau) - math.pi / 2) * 0.9 + 0.1)
        sky = (
            int(10 + 70 * sun),
            int(16 + 90 * sun),
            int(32 + 120 * sun),
        )
        self.screen.fill(sky)

        if self.clouds_enabled:
            for i in range(14):
                px = (i * 173 + int(self.pos_x * 0.2)) % (self.width + 260) - 130
                py = 80 + (i * 47) % 150
                pygame.draw.ellipse(self.screen, (220, 232, 248, 120), (px, py, 170, 40))

        tiles = []
        step = 6
        rd = self.render_distance
        base_cx = int(self.pos_x // step)
        base_cz = int(self.pos_z // step)

        for tz in range(-rd, rd + 1):
            for tx in range(-rd, rd + 1):
                wx = (base_cx + tx) * step
                wz = (base_cz + tz) * step
                h = terrain_height(wx, wz, self.seed)
                proj = self._project(wx, wz, h)
                if proj is None:
                    continue
                sx, sy, p = proj
                fog_mix = clamp((p / 120.0) * (1.0 - self.fog), 0.08, 1.0)
                color = terrain_color(h)
                shaded = (
                    int(color[0] * fog_mix),
                    int(color[1] * fog_mix),
                    int(color[2] * fog_mix),
                )
                size = max(1, int(0.5 + p * 2.2))
                depth = wz - self.pos_z
                tiles.append((depth, sx, sy, size, shaded))

        tiles.sort(reverse=True)
        for _, sx, sy, size, color in tiles:
            pygame.draw.rect(self.screen, color, (int(sx), int(sy), size, size))

        for saucer in self.saucers:
            proj = self._project(saucer.x, saucer.z, saucer.y)
            if proj is None:
                continue
            sx, sy, p = proj
            r = max(2, int(3 + p * 0.9))
            pygame.draw.ellipse(self.screen, (190, 208, 230), (sx - r * 2, sy - r * 0.8, r * 4, r * 1.4))
            pygame.draw.circle(self.screen, (120, 220, 245), (int(sx), int(sy - r * 0.3)), max(2, r // 2))

    def _draw_hud(self) -> None:
        cx = self.width // 2
        cy = self.height // 2
        pygame.draw.line(self.screen, (204, 235, 255), (cx - 8, cy), (cx + 8, cy), 1)
        pygame.draw.line(self.screen, (204, 235, 255), (cx, cy - 8), (cx, cy + 8), 1)

        heading = ((-math.degrees(self.yaw) % 360.0) + 360.0) % 360.0
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        direction = dirs[round(heading / 45) % len(dirs)]

        lines = [
            f"X:{self.pos_x:7.1f}  Y:{self.pos_y:6.1f}  Z:{self.pos_z:7.1f}",
            f"Speed: {self.speed_multiplier:.1f}x",
            f"FPS: {self.fps}",
            f"Heading: {direction}",
        ]
        y = 12
        for line in lines:
            surf = self.font.render(line, True, (214, 232, 255))
            self.screen.blit(surf, (12, y))
            y += 22

        self._draw_minimap()

    def _draw_minimap(self) -> None:
        w = 155
        h = 155
        x0 = self.width - w - 14
        y0 = self.height - h - 14
        pygame.draw.rect(self.screen, (10, 20, 40), (x0, y0, w, h), border_radius=8)
        pygame.draw.rect(self.screen, (80, 132, 184), (x0, y0, w, h), 1, border_radius=8)

        center = (x0 + w // 2, y0 + h // 2)
        pygame.draw.circle(self.screen, (44, 73, 106), center, 54, 1)
        pygame.draw.circle(self.screen, (92, 255, 160), center, 3)
        tip = (
            int(center[0] + math.sin(self.yaw) * 24),
            int(center[1] - math.cos(self.yaw) * 24),
        )
        pygame.draw.line(self.screen, (170, 215, 255), center, tip, 2)

    def _draw_splash(self) -> None:
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((6, 10, 20, 210))
        self.screen.blit(overlay, (0, 0))

        title = self.title_font.render("VOXEL SKYWAYS", True, (224, 242, 255))
        subtitle = self.font.render("Desktop Edition (less browser jitter)", True, (179, 214, 248))
        hint = self.font.render("Press ENTER to start", True, (196, 230, 255))

        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, self.height // 2 - 110))
        self.screen.blit(subtitle, (self.width // 2 - subtitle.get_width() // 2, self.height // 2 - 58))
        self.screen.blit(hint, (self.width // 2 - hint.get_width() // 2, self.height // 2 - 10))

        controls = [
            "W/A/S/D move",
            "Space ascend, Ctrl descend",
            "Mouse look",
            "Esc options",
        ]
        for i, text in enumerate(controls):
            surf = self.font.render(text, True, (192, 219, 248))
            self.screen.blit(surf, (self.width // 2 - surf.get_width() // 2, self.height // 2 + 30 + i * 22))

    def _draw_menu(self) -> None:
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((8, 12, 22, 185))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(self.width // 2 - 300, self.height // 2 - 170, 600, 340)
        pygame.draw.rect(self.screen, (14, 22, 38), panel, border_radius=12)
        pygame.draw.rect(self.screen, (105, 156, 210), panel, 1, border_radius=12)

        lines = [
            "OPTIONS",
            f"Left/Right: Render Distance ({self.render_distance})",
            f"Up/Down: Flight Speed ({self.speed_multiplier:.1f}x)",
            f"1/2: Time of Day ({self.time_of_day:.0f}:00)",
            f"3/4: Fog ({int(self.fog * 100)}%)",
            f"- / = : Saucers ({self.saucers_count})",
            f"C: Clouds ({'ON' if self.clouds_enabled else 'OFF'})",
            "Esc: Resume",
        ]

        y = panel.y + 30
        for i, line in enumerate(lines):
            color = (225, 242, 255) if i == 0 else (198, 224, 250)
            font = self.title_font if i == 0 else self.font
            surf = font.render(line, True, color)
            self.screen.blit(surf, (panel.x + 26, y))
            y += 42 if i == 0 else 34

    def run(self, max_frames: int | None = None) -> int:
        frames = 0
        while self.running:
            dt = min(self.clock.tick(90) / 1000.0, 0.05)
            self.fps = int(self.clock.get_fps())

            self._process_events()
            self._update(dt)

            self._draw_world()
            self._draw_hud()

            if not self.started:
                self._draw_splash()
            if self.menu_open:
                self._draw_menu()

            pygame.display.flip()

            frames += 1
            if max_frames is not None and frames >= max_frames:
                break

        pygame.quit()
        return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Voxel Skyways desktop game")
    parser.add_argument("--width", type=int, default=SCREEN_W)
    parser.add_argument("--height", type=int, default=SCREEN_H)
    parser.add_argument("--headless", action="store_true", help="Run with SDL dummy video driver")
    parser.add_argument("--max-frames", type=int, default=None, help="Stop after N frames (useful for CI checks)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.headless:
        import os

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    game = VoxelSkywaysGame(args.width, args.height, headless=args.headless)
    return game.run(max_frames=args.max_frames)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
