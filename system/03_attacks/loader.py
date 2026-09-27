# -*- coding: utf-8 -*-
"""
system/03_attacks/loader.py
=============================
Torres de ataque:
    - Integrante do LAISER: gera robôs sacrificiais que andam pela
      linha e explodem ao encostar no primeiro zumbi, causando dano;
    - Computador: atira "códigos" (projétil reto) no primeiro zumbi
      da própria linha;
    - Canhão: dispara um meteoro na área com mais zumbis agrupados
      (dano em área, não precisa ser exatamente a mesma linha).

Ficam guardadas em context["placed_attacks"] e na matriz do
tabuleiro (context["board"]["grid"]), igual às defesas.
"""
import math
import pygame
import shared_helpers as sh

COOLDOWNS = {"laser": 3.2, "computador": 1.6, "canhao": 4.5}
DAMAGE = {"laser": 45, "computador": 12, "canhao": 70}
CANHAO_RADIUS = 90
ROBOT_SPEED = 140

_IMAGES = {}


def setup(context):
    context["placed_attacks"] = []
    context["projectiles"] = []
    context["robots"] = []

    for kind, stats in sh.ATTACK_STATS.items():
        _IMAGES[kind] = sh.load_image(stats["image"], (100, 100))

    context["_sfx_computador"] = sh.load_sound("sfx_computador.wav")
    context["_sfx_canhao"] = sh.load_sound("sfx_canhao.wav")
    context["_sfx_laser"] = sh.load_sound("sfx_laser.wav")


def _closest_enemy_in_row(context, row):
    best, best_x = None, None
    for z in context.get("enemies", []):
        if z["row"] != row or z["hp"] <= 0:
            continue
        if best is None or z["x"] < best_x:
            best, best_x = z, z["x"]
    return best


def _best_cluster_target(context):
    enemies = [z for z in context.get("enemies", []) if z["hp"] > 0]
    if not enemies:
        return None
    best, best_score = None, -1
    for z in enemies:
        score = sum(
            1 for o in enemies
            if math.hypot(o["x"] - z["x"], o["y"] - z["y"]) <= CANHAO_RADIUS
        )
        if score > best_score:
            best, best_score = z, score
    return best


def update(context, dt):
    if context.get("game_over") or context.get("paused"):
        return

    # ---- disparo das torres (respeitando o cooldown de cada uma) ----
    for att in context["placed_attacks"]:
        att["cooldown"] = max(0.0, att.get("cooldown", 0.0) - dt)
        if att["cooldown"] > 0:
            continue
        origin = context["board_cell_center"](att["row"], att["col"])

        if att["kind"] == "computador" and _closest_enemy_in_row(context, att["row"]):
            context["projectiles"].append({
                "kind": "computador", "x": float(origin[0]), "y": float(origin[1]),
                "row": att["row"], "speed": 520, "damage": DAMAGE["computador"],
            })
            att["cooldown"] = COOLDOWNS["computador"]
            sh.play_sfx(context.get("_sfx_computador"), 0.5)

        elif att["kind"] == "canhao":
            target = _best_cluster_target(context)
            if target is not None:
                context["projectiles"].append({
                    "kind": "canhao", "x": float(origin[0]), "y": float(origin[1]),
                    "target_x": target["x"], "target_y": target["y"],
                    "travel_t": 0.0, "travel_dur": 0.5, "damage": DAMAGE["canhao"],
                })
                att["cooldown"] = COOLDOWNS["canhao"]
                sh.play_sfx(context.get("_sfx_canhao"), 0.6)

        elif att["kind"] == "laser" and _closest_enemy_in_row(context, att["row"]):
            context["robots"].append({"x": float(origin[0]), "y": float(origin[1]), "row": att["row"]})
            att["cooldown"] = COOLDOWNS["laser"]
            sh.play_sfx(context.get("_sfx_laser"), 0.5)

    # ---- projéteis do computador (retos, na própria linha) ----
    alive_proj = []
    for p in context["projectiles"]:
        if p["kind"] == "computador":
            p["x"] += p["speed"] * dt
            target = _closest_enemy_in_row(context, p["row"])
            hit = target is not None and p["x"] >= target["x"] - 20
            if hit:
                target["hp"] -= p["damage"]
            elif p["x"] < context["board"]["x"] + context["board"]["w"] + 60:
                alive_proj.append(p)

        elif p["kind"] == "canhao":
            p["travel_t"] += dt
            if p["travel_t"] >= p["travel_dur"]:
                for z in context.get("enemies", []):
                    if math.hypot(z["x"] - p["target_x"], z["y"] - p["target_y"]) <= CANHAO_RADIUS:
                        z["hp"] -= p["damage"]
                context.setdefault("fx", []).append(
                    {"x": p["target_x"], "y": p["target_y"], "t": 0.0}
                )
            else:
                alive_proj.append(p)
    context["projectiles"] = alive_proj

    # ---- robôs sacrificiais do LAISER ----
    alive_robots = []
    for r in context["robots"]:
        target = _closest_enemy_in_row(context, r["row"])
        r["x"] += ROBOT_SPEED * dt
        exploded = False
        if target is not None and abs(target["x"] - r["x"]) < 26:
            target["hp"] -= DAMAGE["laser"]
            exploded = True
        elif r["x"] > context["board"]["x"] + context["board"]["w"] + 60:
            exploded = True
        if not exploded:
            alive_robots.append(r)
    context["robots"] = alive_robots


def draw(context, surface):
    for att in context["placed_attacks"]:
        rect = context["board_cell_rect"](att["row"], att["col"])
        stats = sh.ATTACK_STATS[att["kind"]]
        img = _IMAGES.get(att["kind"])
        if sh.has_image(img):
            sh.blit_scaled(surface, img, rect.inflate(-8, -8))
        else:
            inset = rect.inflate(-16, -16)
            pygame.draw.rect(surface, stats["color"], inset, border_radius=6)
            pygame.draw.rect(surface, (10, 10, 10), inset, width=2, border_radius=6)
            label = sh.get_font(12, bold=True).render(stats["label"][:3].upper(), True, sh.COL_TEXT)
            surface.blit(label, label.get_rect(center=inset.center))

    for p in context["projectiles"]:
        if p["kind"] == "computador":
            pygame.draw.circle(surface, (80, 220, 120), (int(p["x"]), int(p["y"])), 6)
        else:
            t = min(1.0, p["travel_t"] / p["travel_dur"])
            x = sh.lerp(p["x"], p["target_x"], t)
            y = sh.lerp(p["y"], p["target_y"], t) - 60 * math.sin(math.pi * t)
            pygame.draw.circle(surface, (200, 120, 40), (int(x), int(y)), 10)

    for r in context["robots"]:
        rect = pygame.Rect(int(r["x"]) - 10, int(r["y"]) - 10, 20, 20)
        pygame.draw.rect(surface, (200, 60, 60), rect, border_radius=4)
