import math
import os
import random
import sys
import time
from typing import List
from typing import Optional
from typing import Tuple

import feedparser
import instabot

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from melvec.vec2 import Vec2
from melvec.vec3 import Vec3

sys.path.append("../../")
from credentials import InstagramBot

IMG_WIDTH = 1080
IMG_HEIGHT = 1080
PADDING = 96
IMG_OUTPUT_DIR = "../image_output/out.jpg"


def get_data(mode: str = "days") -> Optional[List[Tuple[str, str]]]:
    feed = feedparser.parse(f"https://skolmaten.se/anna-whitlocks-gymnasium/rss/{mode}/")

    data = []
    for entry in feed["entries"]:
        data.append((entry["title"], entry["summary"].replace("<br />", "\n")))

    return data


def wrap_text(text: str, font: ImageFont = None, line_length: int = IMG_WIDTH - PADDING * 2) -> str:
    lines = ['']
    for word in text.split():
        line = f'{lines[-1]} {word}'.strip()
        if font.getlength(line) <= line_length:
            lines[-1] = line
        else:
            lines.append(word)
    return '\n'.join(lines)


def rainbow(angle: float) -> Tuple[int, int, int]:
    r = math.sin(angle) * 0.5 + 0.5
    g = math.sin(angle + 2 * math.pi / 3) * 0.5 + 0.5
    b = math.sin(angle + 4 * math.pi / 3) * 0.5 + 0.5
    return tuple(map(lambda x: math.floor(x * 255), (r, g, b)))


def gradient(start_color: Vec3, end_color: Vec3) -> Image.Image:
    gradient_vector = Vec2(IMG_WIDTH, IMG_HEIGHT)
    gradient_nvector = gradient_vector / gradient_vector.magnitude()

    gradient_img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT))
    pixels = gradient_img.load()
    for y in range(IMG_WIDTH):
        for x in range(IMG_HEIGHT):
            brightness = (Vec2(x, y) / gradient_vector.magnitude()).dot(gradient_nvector)
            color = end_color * brightness + start_color * (1 - brightness)
            color = int(color.x), int(color.y), int(color.z)
            pixels[x, y] = color
    return gradient_img


def generate_image(data: List[Tuple[str, str]], save_path: str = IMG_OUTPUT_DIR) -> None:
    angle = random.randint(0, 6283) / 1000
    background = gradient(Vec3(*rainbow(angle)), Vec3(*rainbow(angle + math.pi)))
    foreground = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), (29, 29, 29))

    title_font_size = 40 + 4 * (5 - len(data))
    summary_font_size = 32 + 4 * (5 - len(data))
    title_font = ImageFont.truetype("arial.ttf", title_font_size)
    summary_font = ImageFont.truetype("arial.ttf", summary_font_size)
    indent = summary_font.getlength("    ")

    offset = 0

    for title, summary in data:
        summary_text = wrap_text(summary, summary_font, 1080 - 2 * PADDING - indent)
        offset += title_font_size * 2 + summary_font_size * (len(summary_text.split("\n")) + 1.5)

    offset = (IMG_HEIGHT - offset) // 2

    mask = Image.new("1", (IMG_WIDTH, IMG_HEIGHT))
    mask_draw = ImageDraw.Draw(mask)

    for (title, summary) in data:
        title_text = wrap_text(title, title_font, 1080 - 2 * PADDING)
        summary_text = wrap_text(summary, summary_font, 1080 - 2 * PADDING - indent)

        title_pos = (PADDING, PADDING + offset)
        summary_pos = (title_pos[0] + indent, title_pos[1] + summary_font_size * 1.5)

        offset += title_font_size * 2 + summary_font_size * (len(summary_text.split("\n")))

        mask_draw.text(title_pos, title_text, 1, title_font)
        mask_draw.text(summary_pos, summary_text, 1, summary_font)

    img = Image.composite(background, foreground, mask)
    img.save(save_path, subsampling=4, quality=100)


def main() -> None:
    if not os.path.exists("../image_output/out.jpg"):
        if not os.path.exists("../image_output"):
            os.mkdir("../image_output")
        open("../image_output/out.jpg", "w").close()
            
    
    if os.path.exists("./config/aw_lunch_uuid_and_cookie.json"):
        os.remove("./config/aw_lunch_uuid_and_cookie.json")

    bot = instabot.Bot()
    bot.login(username=InstagramBot.username, password=InstagramBot.password)

    latest_title = ""
    while True:
        data = get_data()
        print(data)
        if not data:
            time.sleep(10)
            continue

        today = data[0][0]

        if today == latest_title:
            time.sleep(10)
            continue

        if any(word.lower() in ["måndag", "monday"] for word in today.split()):
            data = get_data("weeks")
            generate_image(data)
            bot.upload_photo(IMG_OUTPUT_DIR)
            while not os.path.exists(f"{IMG_OUTPUT_DIR}.REMOVE_ME"):
                pass
            os.remove(f"{IMG_OUTPUT_DIR}.REMOVE_ME")

        data = get_data()
        generate_image(data)
        bot.upload_photo(IMG_OUTPUT_DIR)
        while not os.path.exists(f"{IMG_OUTPUT_DIR}.REMOVE_ME"):
            pass
        os.remove(f"{IMG_OUTPUT_DIR}.REMOVE_ME")

        latest_title = today
        time.sleep(10)


if __name__ == "__main__":
    main()
