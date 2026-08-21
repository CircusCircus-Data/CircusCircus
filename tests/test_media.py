"""Tests for safe post image and video links."""

import unittest

from forum.media import valid_image_url, valid_video_url, video_embed_url


class MediaValidationTests(unittest.TestCase):
    def test_supported_image_formats(self):
        for extension in ("jpg", "jpeg", "png", "gif", "webp"):
            with self.subTest(extension=extension):
                self.assertTrue(valid_image_url(f"https://cdn.example/image.{extension}"))

    def test_rejects_unsafe_or_unsupported_images(self):
        self.assertFalse(valid_image_url("http://example.com/image.jpg"))
        self.assertFalse(valid_image_url("javascript:alert(1)"))
        self.assertFalse(valid_image_url("https://example.com/image.svg"))
        self.assertFalse(valid_image_url("https://example.com/image.jpg.exe"))
        self.assertFalse(valid_image_url("https://example.com/" + "a" * 2048 + ".jpg"))

    def test_youtube_links_use_privacy_enhanced_embed(self):
        expected = "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
        self.assertEqual(
            video_embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            expected,
        )
        self.assertEqual(
            video_embed_url("https://youtu.be/dQw4w9WgXcQ"),
            expected,
        )

    def test_vimeo_links_use_player_embed(self):
        self.assertEqual(
            video_embed_url("https://vimeo.com/123456789"),
            "https://player.vimeo.com/video/123456789",
        )

    def test_rejects_unsupported_video_providers_and_ids(self):
        self.assertFalse(valid_video_url("https://example.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(valid_video_url("https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(valid_video_url("https://www.youtube.com/watch?v=bad"))
        self.assertFalse(valid_video_url("http://vimeo.com/123456789"))

    def test_blank_optional_links_are_valid(self):
        self.assertTrue(valid_image_url(""))
        self.assertTrue(valid_video_url(""))


if __name__ == "__main__":
    unittest.main()
