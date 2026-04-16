#!/usr/bin/env python3
"""AutoAffil メインエントリーポイント"""
import argparse
import sys
from utils.niche_selector import NicheSelector
from utils.sheets_logger import SheetsLogger


def main():
    parser = argparse.ArgumentParser(description="AutoAffil content runner")
    parser.add_argument("--platform", required=True,
                        choices=["x", "medium", "tiktok", "youtube", "instagram"])
    parser.add_argument("--format", default="shorts", choices=["shorts", "longform"])
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't post")
    args = parser.parse_args()

    niche_selector = NicheSelector()
    logger         = SheetsLogger()
    niche, product = niche_selector.get_next()

    print(f"\n[AutoAffil] Platform={args.platform} | Niche={niche} | Product={product['product']}")

    try:
        if args.platform == "x":
            from generators.x_generator import XGenerator
            from posters.x_poster import XPoster
            content = XGenerator().generate(niche, product)
            print(f"\n  Main post:\n  {content['main_post']}")
            if args.dry_run:
                print("\n  [dry-run] Skipping post")
                return
            result = XPoster().post(content)

        elif args.platform == "medium":
            from generators.medium_generator import MediumGenerator
            from posters.medium_poster import MediumPoster
            content = MediumGenerator().generate(niche, product)
            print(f"\n  Title: {content.get('title','')}")
            print(f"  Tags:  {content.get('tags','')}")
            if args.dry_run:
                print("\n  [dry-run] Skipping post")
                return
            result = MediumPoster().post(content)

        elif args.platform == "instagram":
            from generators.instagram_generator import InstagramGenerator
            from posters.instagram_poster import InstagramPoster
            content = InstagramGenerator().generate(niche, product)
            print(f"\n  Caption: {content.get('caption','')[:100]}...")
            print(f"  Hashtags: {' '.join(content.get('hashtags',[]))}")
            if args.dry_run:
                print("\n  [dry-run] Skipping post")
                return
            result = InstagramPoster().post(content)

        elif args.platform == "youtube":
            from generators.youtube_generator import YouTubeGenerator
            from posters.youtube_poster import YouTubePoster
            content = YouTubeGenerator().generate(niche, product, fmt=args.format)
            print(f"\n  Title: {content.get('title','')}")
            print(f"  Format: {args.format}")
            if args.dry_run:
                print("\n  [dry-run] Skipping post")
                return
            result = YouTubePoster().post(content, fmt=args.format)

        elif args.platform == "tiktok":
            from generators.tiktok_generator import TikTokGenerator
            from posters.tiktok_poster import TikTokPoster
            content = TikTokGenerator().generate(niche, product)
            print(f"\n  Caption: {content.get('caption','')[:100]}...")
            if args.dry_run:
                print("\n  [dry-run] Skipping post")
                return
            result = TikTokPoster().post(content)

        else:
            print(f"  ⚠️  Platform '{args.platform}' not yet implemented")
            return

        logger.log_success(args.platform, niche, product, result)
        print(f"\n[AutoAffil] ✅ SUCCESS: {result}")

    except Exception as e:
        logger.log_error(args.platform, niche, product, str(e))
        print(f"\n[AutoAffil] ❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
