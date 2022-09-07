import os
import sys
import time
from typing import List
from typing import Optional
from typing import Tuple

import feedparser
import instabot
import PIL
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

sys.path.append("../../")
from credentials import InstagramBot


class AwLunch:
    def __init__(self, username, password):
        self.bot = instabot.Bot()
        self.bot.login(username=username, password=password)

    def get_menu(self, mode: str = "days") -> Optional[List[Tuple[str, str]]]:
        feed = feedparser.parse(f"https://skolmaten.se/anna-whitlocks-gymnasium/rss/{mode}/")
        data = []

        for entry in feed["entries"]:
            data.append((entry["title"], entry["summary"]))

        return data

    def wrap_text(self, text: str, font: PIL.ImageFont = None, line_length: int = 540) -> str:
        lines = ['']
        for word in text.split():
            line = f'{lines[-1]} {word}'.strip()
            if font.getlength(line) <= line_length:
                lines[-1] = line
            else:
                lines.append(word)
        return '\n'.join(lines)

    def generate_image(self,data: List[Tuple[str, str]], save_path: str = "../image_output/out.jpg") -> None:
        img = Image.new("RGB", (1080, 1080), (29, 29, 29, 255))
        draw = ImageDraw.Draw(img)

        title_font_size = 40 + 4 * (5 - len(data))
        summary_font_size = 32 + 4 * (5 - len(data))
        title_font = ImageFont.truetype("arial.ttf", title_font_size)
        summary_font = ImageFont.truetype("arial.ttf", summary_font_size)

        padding = 135
        indent = summary_font.getlength("    ")

        offset = padding * 2

        for title, summary in data:
            summary_text = self.wrap_text(summary, summary_font, 1080 - 2 * padding - indent)
            offset += title_font_size * 2 + summary_font_size * (len(summary_text.split("\n")))

        offset = (1080 - offset) // 2

        for (title, summary) in data:
            title_text = self.wrap_text(title, title_font, 1080 - 2 * padding)
            summary_text = self.wrap_text(summary, summary_font, 1080 - 2 * padding - indent)

            title_pos = (padding, padding + offset)
            summary_pos = (title_pos[0] + indent, title_pos[1] + summary_font_size * 1.5)

            offset += title_font_size * 2 + summary_font_size * (len(summary_text.split("\n")))

            draw.text(title_pos, title_text, font=title_font)
            draw.text(summary_pos, summary_text, font=summary_font)

        img.save(save_path)

    def run(self):
        latest_title = ""
        while True:
            data = self.get_menu()
            today = data[0][0]

            if today == latest_title:
                time.sleep(10)
                continue

            if any(word in ["Måndag", "måndag", "Monday", "monday"] for word in today):
                data = self.get_menu("weeks")
                self.generate_image(data)
                self.bot.upload_photo("../image_output/out.jpg")
                while not os.path.exists("../image_output/out.jpg.REMOVE_ME"):
                    pass

                os.remove("../image_output/out.jpg.REMOVE_ME")

            data = self.get_menu()
            self.generate_image(data)
            self.bot.upload_photo("../image_output/out.jpg")
            while not os.path.exists("../image_output/out.jpg.REMOVE_ME"):
                pass

            os.remove("../image_output/out.jpg.REMOVE_ME")

            latest_title = today
            time.sleep(10)


if __name__ == "__main__":
    if os.path.exists("./config/aw_lunch_uuid_and_cookie.json"):
        os.remove("./config/aw_lunch_uuid_and_cookie.json")

    aw_lunch = AwLunch(InstagramBot.username, InstagramBot.password)
    aw_lunch.run()
