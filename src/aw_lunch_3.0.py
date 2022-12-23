import math
import os
from pathlib import Path
from random import uniform
import sys
import time
from typing import List, Optional, Tuple

import feedparser
from instagrapi import Client
from melvec import Vec2, Vec3
from PIL import Image, ImageDraw, ImageFont

sys.path.append("../../")
from credentials import InstagramBot

FEED_URL = "https://skolmaten.se/anna-whitlocks-gymnasium/rss/"
FONT_PATH = Path("../resources/CaviarDreams.ttf")
IMAGE_OUTPUT_PATH = Path("../image_output/out.jpg")
IMAGE_FILE_NAME = "out.jpg"
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1080
IMAGE_OUTER_PADDING = 96
IMAGE_INNER_PADDING = 16
IMAGE_BACKGROUND = (29, 29, 29)
IMAGE_FOREGROUND = (58, 58, 58)
IMAGE_SUPERSAMPLING_SCALE = 2
GRADIENT_COLOR_OFFSET = 2 * math.pi / 3
RSS_POLL_DELAY = 10


def get_data(feed_url: str, mode: str = "days") -> Optional[List[Tuple[str, str, time.struct_time]]]:
    if not feed_url.endswith('/'):
        feed_url += '/'

    feed = feedparser.parse(f"{feed_url}{mode}/")

    data = []
    for entry in feed["entries"]:
        title = entry["title"]
        summary = entry["summary"].replace("<br />", '\n')
        published = entry["published_parsed"]

        data.append((title, summary, published))

    return data


def wrap_text(text: str, font: ImageFont, max_width: int) -> List[str]:
    lines = ['']
    word = ''

    for char in text.strip() + ' ':
        if char == '\n':
            lines[-1] += f" {word}"
            lines.append('')
            word = ''
            continue

        word += char

        if font.getlength(f"{lines[-1]} {word}") > max_width:
            lines.append('')

        if char == ' ':
            lines[-1] += ' ' + word
            word = ''

    return list(map(str.strip, lines))


def rainbow(angle: float) -> Vec3:
    r = math.sin(angle) * 0.5 + 0.5
    g = math.sin(angle + 2 * math.pi / 3) * 0.5 + 0.5
    b = math.sin(angle + 4 * math.pi / 3) * 0.5 + 0.5
    return Vec3(r, g, b) * 255


def gradient(start_color, end_color, width, height) -> Image:
    gradient_vector = Vec2(width, height)
    gradient_normal_vector = gradient_vector / gradient_vector.magnitude()

    gradient_image = Image.new("RGB", (width, height))
    pixels = gradient_image.load()

    for y in range(width):
        for x in range(height):
            brightness = (Vec2(x, y) / gradient_vector.magnitude()).dot(gradient_normal_vector)
            color = end_color * brightness + start_color * (1 - brightness)
            color = tuple(map(int, color))
            pixels[x, y] = color

    return gradient_image


def create_image(data: List[Tuple[str, str, time.struct_time]], font: Path = FONT_PATH) -> Image:
    width = IMAGE_WIDTH * IMAGE_SUPERSAMPLING_SCALE
    height = IMAGE_HEIGHT * IMAGE_SUPERSAMPLING_SCALE
    outer_padding = IMAGE_OUTER_PADDING * IMAGE_SUPERSAMPLING_SCALE
    inner_padding = IMAGE_INNER_PADDING * IMAGE_SUPERSAMPLING_SCALE
    title_font = ImageFont.truetype(str(font), inner_padding * 3)
    summary_font = ImageFont.truetype(str(font), inner_padding * 2)

    image = Image.new("RGB", (width, height), IMAGE_BACKGROUND)
    draw = ImageDraw.Draw(image)

    angle = uniform(0, math.pi * 2)
    gradient_image = gradient(rainbow(angle), rainbow(angle + GRADIENT_COLOR_OFFSET), width, height)

    text_mask = Image.new('1', (width, height))
    mask_draw = ImageDraw.Draw(text_mask)

    required_height = inner_padding * (len(data) - 1)

    for i, (_, summary, _) in enumerate(data):
        summary_lines = wrap_text(summary, summary_font, width - (outer_padding + 2 * inner_padding) * 2)
        extra_spacing = (len(summary_lines) - 1) * 4 * IMAGE_SUPERSAMPLING_SCALE
        required_height += inner_padding * (8 + 2 * len(summary_lines)) + extra_spacing

    y = height // 2 - required_height // 2

    for i, (title, summary, _) in enumerate(data):
        summary_lines = wrap_text(summary, summary_font, width - (outer_padding + 2 * inner_padding) * 2)
        extra_spacing = (len(summary_lines) - 1) * 4 * IMAGE_SUPERSAMPLING_SCALE
        day_box_height = inner_padding * (8 + 2 * len(summary_lines)) + extra_spacing
        summary_box_height = inner_padding * (1 + 2 * len(summary_lines)) + extra_spacing

        draw.rounded_rectangle((outer_padding,
                                y,
                                width - outer_padding,
                                y + day_box_height),
                               outer_padding // 4, fill=IMAGE_FOREGROUND)

        draw.rounded_rectangle((outer_padding + inner_padding,
                                y + inner_padding,
                                outer_padding + 3 * inner_padding + title_font.getlength(title),
                                y + 5 * inner_padding),
                               outer_padding // 4, fill=IMAGE_BACKGROUND)

        draw.rounded_rectangle((outer_padding + inner_padding * 3,
                                y + 6 * inner_padding,
                                width - outer_padding - inner_padding * 3,
                                y + 6 * inner_padding + summary_box_height),
                               outer_padding // 4, fill=IMAGE_BACKGROUND)

        mask_draw.text((outer_padding + 2 * inner_padding, y + inner_padding + 4 * IMAGE_SUPERSAMPLING_SCALE),
                       title,
                       1,
                       font=title_font)

        mask_draw.text((outer_padding + 4 * inner_padding, y + 6 * inner_padding + 4 * IMAGE_SUPERSAMPLING_SCALE),
                       '\n'.join(summary_lines),
                       1,
                       font=summary_font)

        y += day_box_height + inner_padding

    image = Image.composite(gradient_image, image, text_mask).resize((IMAGE_WIDTH, IMAGE_HEIGHT),
                                                                     resample=Image.Resampling.LANCZOS)

    return image


def main() -> None:
    if not os.path.exists(IMAGE_OUTPUT_PATH.parent):
        os.mkdir(IMAGE_OUTPUT_PATH.parent)

    client = Client()

    print(f"Attempting login to {InstagramBot.username}...")
    client.login(InstagramBot.username, InstagramBot.password)
    print("Login successful!")

    last_day = None
    while True:
        time.sleep(RSS_POLL_DELAY)
        data = get_data(FEED_URL)

        if not data:
            continue

        published = data[0][2]

        if published == last_day:
            continue

        last_day = published
        print(f"RSS feed updated. Data: {data}")

        if published.tm_wday == 0:
            data = get_data(FEED_URL, "weeks")

        print("Generating image...")
        create_image(data).save(IMAGE_OUTPUT_PATH, quality=100)
        print(f"Done! image created and saved to {IMAGE_OUTPUT_PATH}.")

        print("Uploading image...")
        client.photo_upload(IMAGE_OUTPUT_PATH, '')
        print("Done! Image successfully uploaded.")

        print("Waiting for RSS feed to update...")


if __name__ == "__main__":
    main()