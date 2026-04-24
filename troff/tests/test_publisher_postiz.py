import os
import unittest
from typing import Optional
from unittest.mock import Mock, patch

from app.models import Platform, SocialPost
from app.services.publisher import PublishError, _publish_social_postiz


class PostizPublisherTests(unittest.TestCase):
    def _social_post(self, platform: Platform = Platform.linkedin) -> SocialPost:
        return SocialPost(
            package_id=1,
            platform=platform,
            body="hello world",
            asset_url="",
            reddit_subreddit="billwithbomi",
            reddit_title="",
        )

    def _env(self, **overrides: str) -> dict[str, str]:
        base = {
            "POSTIZ_API_KEY": "postiz-test-key",
            "POSTIZ_INTEGRATION_LINKEDIN": "integration-linkedin-1",
            "POSTIZ_INTEGRATION_REDDIT": "integration-reddit-1",
        }
        base.update(overrides)
        return base

    def _response(self, status_code: int, body: Optional[dict] = None, text: str = "") -> Mock:
        resp = Mock()
        resp.status_code = status_code
        resp.text = text
        resp.json.return_value = body if body is not None else {}
        return resp

    def test_postiz_url_normalization_without_public_v1(self) -> None:
        env = self._env(POSTIZ_API_URL="https://api.postiz.com")
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "app.services.publisher.requests.post",
                return_value=self._response(200, {"id": "post-1"}),
            ) as mock_post:
                _publish_social_postiz(self._social_post())

        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "https://api.postiz.com/public/v1/posts")

    def test_postiz_url_normalization_with_public_v1(self) -> None:
        env = self._env(POSTIZ_API_URL="https://api.postiz.com/public/v1")
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "app.services.publisher.requests.post",
                return_value=self._response(200, {"id": "post-2"}),
            ) as mock_post:
                _publish_social_postiz(self._social_post())

        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "https://api.postiz.com/public/v1/posts")

    def test_missing_postiz_api_key_raises_expected_error(self) -> None:
        env = {
            "POSTIZ_API_URL": "https://api.postiz.com",
            "POSTIZ_INTEGRATION_LINKEDIN": "integration-linkedin-1",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(PublishError) as ctx:
                _publish_social_postiz(self._social_post())

        self.assertEqual(ctx.exception.code, "postiz_api_key_missing")

    def test_missing_postiz_integration_raises_expected_error(self) -> None:
        env = {
            "POSTIZ_API_URL": "https://api.postiz.com",
            "POSTIZ_API_KEY": "postiz-test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(PublishError) as ctx:
                _publish_social_postiz(self._social_post())

        self.assertEqual(ctx.exception.code, "postiz_integration_missing")

    def test_postiz_publish_success_returns_external_id(self) -> None:
        env = self._env(POSTIZ_API_URL="https://api.postiz.com")
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "app.services.publisher.requests.post",
                return_value=self._response(200, {"id": "post-123"}),
            ):
                external_id = _publish_social_postiz(self._social_post())

        self.assertEqual(external_id, "post-123")

    def test_postiz_publish_failures_raise_expected_error(self) -> None:
        env = self._env(POSTIZ_API_URL="https://api.postiz.com")
        for status_code in (401, 403, 429, 500):
            with self.subTest(status_code=status_code):
                with patch.dict(os.environ, env, clear=True):
                    with patch(
                        "app.services.publisher.requests.post",
                        return_value=self._response(status_code, text="provider error"),
                    ):
                        with self.assertRaises(PublishError) as ctx:
                            _publish_social_postiz(self._social_post())

                self.assertEqual(ctx.exception.code, "postiz_publish_failed")
                self.assertEqual(ctx.exception.http_status, status_code)

    def test_reddit_publish_uses_postiz_integration(self) -> None:
        env = self._env(POSTIZ_API_URL="https://api.postiz.com")
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "app.services.publisher.requests.post",
                return_value=self._response(200, {"id": "reddit-post-1"}),
            ) as mock_post:
                external_id = _publish_social_postiz(self._social_post(Platform.reddit))

        self.assertEqual(external_id, "reddit-post-1")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["posts"][0]["integration"]["id"], "integration-reddit-1")


if __name__ == "__main__":
    unittest.main()
