from __future__ import annotations

import base64
import io
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from backend.modules.aion_business.runtime.local_asset_store import LocalAssetStore
except Exception:  # pragma: no cover
    LocalAssetStore = None  # type: ignore[assignment]

try:
    from backend.modules.vault.ai_provider_key_store import get_ai_provider_secret
except Exception:  # pragma: no cover
    get_ai_provider_secret = None  # type: ignore[assignment]


class ImageGenerationService:
    """
    Local-first image generation service.

    Updated behavior:
    - supports single-image generation
    - supports multi-card carousel slide generation
    - normalizes prompt text to avoid unicode / transport failures
    - persists generated image bytes locally
    - prefers LocalAssetStore when available
    - returns stable structured payloads for future provider expansion

    Notes:
    - default social slide generation size uses a supported portrait OpenAI size
    - when generating carousel cards, each card gets its own image
    - optional reference assets can be injected into prompts as guidance
    - frontend can still render inside a 4:5 preview frame
    """

    DEFAULT_SOCIAL_SIZE = "1024x1536"
    DEFAULT_SOCIAL_BACKGROUND = "opaque"
    DEFAULT_SOCIAL_FORMAT = "png"

    CARD_TYPE_ORDER = ["hook", "problem", "solution", "proof", "cta"]

    def __init__(
        self,
        *,
        openai_api_key: Optional[str] = None,
        base_dir: Optional[str | Path] = None,
        asset_store: Optional["LocalAssetStore"] = None,
    ) -> None:
        vault_key = get_ai_provider_secret("openai") if get_ai_provider_secret else ""
        gemini_vault_key = get_ai_provider_secret("gemini") if get_ai_provider_secret else ""
        self.openai_api_key = openai_api_key or vault_key or os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = gemini_vault_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.base_dir = Path(base_dir or ".runtime/local_node/generated_images")

        if asset_store is not None:
            self.asset_store = asset_store
        elif LocalAssetStore is not None:
            try:
                self.asset_store = LocalAssetStore()
            except Exception:
                self.asset_store = None
        else:
            self.asset_store = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate_marketing_image(
        self,
        *,
        prompt: str,
        provider: str = "openai",
        model: str = "gpt-image-1",
        size: str = DEFAULT_SOCIAL_SIZE,
        background: str = DEFAULT_SOCIAL_BACKGROUND,
        output_format: str = DEFAULT_SOCIAL_FORMAT,
        file_stem: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate one marketing image.
        """
        provider_normalized = str(provider or "openai").strip().lower()
        metadata = dict(metadata or {})

        safe_output_format = self._sanitize_output_format(output_format)
        normalized_prompt = self._normalize_prompt(prompt)
        safe_prompt = self._force_ascii(normalized_prompt)
        safe_model = str(model or "gpt-image-1").strip() or "gpt-image-1"
        safe_size = str(size or self.DEFAULT_SOCIAL_SIZE).strip() or self.DEFAULT_SOCIAL_SIZE
        safe_background = (
            str(background or self.DEFAULT_SOCIAL_BACKGROUND).strip()
            or self.DEFAULT_SOCIAL_BACKGROUND
        )

        self._debug("IMAGE SERVICE FILE =", __file__)
        self._debug("IMAGE SERVICE PROMPT ORIGINAL =", repr(str(prompt or "")))
        self._debug("IMAGE SERVICE PROMPT NORMALIZED =", repr(normalized_prompt))
        self._debug("IMAGE SERVICE PROMPT SAFE ASCII =", repr(safe_prompt))
        self._debug("IMAGE SERVICE SIZE =", repr(safe_size))

        return self._generate_single_image(
            provider=provider_normalized,
            model=safe_model,
            prompt_original=str(prompt or ""),
            prompt_normalized=normalized_prompt,
            prompt_safe_ascii=safe_prompt,
            size=safe_size,
            background=safe_background,
            output_format=safe_output_format,
            file_stem=file_stem,
            metadata=metadata,
        )

    def generate_marketing_carousel_cards(
        self,
        *,
        caption: str,
        carousel: List[Any],
        provider: str = "openai",
        model: str = "gpt-image-1",
        size: str = DEFAULT_SOCIAL_SIZE,
        background: str = DEFAULT_SOCIAL_BACKGROUND,
        output_format: str = DEFAULT_SOCIAL_FORMAT,
        file_stem_prefix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        visual_assets: Optional[Dict[str, Any]] = None,
        brand_name: Optional[str] = None,
        primary_channel: str = "Facebook",
        offer: Optional[str] = None,
        audience: Optional[str] = None,
        persona: Optional[str] = None,
        objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate one image per carousel card.

        Returns:
        {
          "ok": bool,
          "provider": "...",
          "model": "...",
          "cards": [...],
          "error": "...optional..."
        }
        """
        provider_normalized = str(provider or "openai").strip().lower()
        safe_model = str(model or "gpt-image-1").strip() or "gpt-image-1"
        safe_size = str(size or self.DEFAULT_SOCIAL_SIZE).strip() or self.DEFAULT_SOCIAL_SIZE
        safe_background = (
            str(background or self.DEFAULT_SOCIAL_BACKGROUND).strip()
            or self.DEFAULT_SOCIAL_BACKGROUND
        )
        safe_output_format = self._sanitize_output_format(output_format)
        metadata = dict(metadata or {})
        visual_assets = dict(visual_assets or {})
        original_image_paths = []
        for asset in list(visual_assets.get("creative_assets") or []):
            if not isinstance(asset, dict):
                continue
            candidate = str(asset.get("file_path") or asset.get("path") or asset.get("url") or "").strip()
            if candidate and Path(candidate).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and Path(candidate).exists():
                original_image_paths.append(candidate)

        slides = self._normalize_carousel_slides(carousel, caption=caption)
        cards: List[Dict[str, Any]] = []
        external_renderer_available = True

        if not slides:
            return {
                "ok": False,
                "provider": provider_normalized,
                "model": safe_model,
                "error": "empty_carousel_cards",
                "cards": [],
                "metadata": metadata,
            }

        for index, slide in enumerate(slides, start=1):
            card_type = self._card_type_for_index(index)
            card_prompt = self._build_carousel_card_prompt(
                card_index=index,
                card_type=card_type,
                headline=slide.get("headline", ""),
                body=slide.get("body", ""),
                caption=caption,
                brand_name=brand_name,
                primary_channel=primary_channel,
                offer=offer,
                audience=audience,
                persona=persona,
                objective=objective,
                visual_assets=visual_assets,
            )

            card_file_stem = self._sanitize_file_stem(
                f"{file_stem_prefix or 'carousel'}_card_{index}"
            )

            card_metadata = {
                **metadata,
                "card_index": index,
                "card_type": card_type,
                "primary_channel": primary_channel,
            }

            original_source = original_image_paths[(index - 1) % len(original_image_paths)] if original_image_paths else ""
            result = (
                self._generate_local_evidence_card(
                    source_path=original_source,
                    headline=slide.get("headline", ""),
                    body=slide.get("body", ""),
                    brand_name=brand_name or "Business",
                    card_type=card_type,
                    file_stem=card_file_stem,
                    metadata={**card_metadata, "source_kind": "business_original"},
                )
                if original_source
                else self.generate_marketing_image(
                    prompt=card_prompt,
                    provider=provider_normalized,
                    model=safe_model,
                    size=safe_size,
                    background=safe_background,
                    output_format=safe_output_format,
                    file_stem=card_file_stem,
                    metadata=card_metadata,
                )
                if external_renderer_available
                else {"ok": False, "error": "external_renderer_unavailable_for_this_batch"}
            )
            if not result.get("ok"):
                if any(marker in str(result.get("error") or "").lower() for marker in ("quota", "credit", "rate", "resource_exhausted")):
                    external_renderer_available = False
                result = self._generate_local_brand_card(
                    headline=slide.get("headline", ""),
                    body=slide.get("body", ""),
                    brand_name=brand_name or "Business",
                    card_type=card_type,
                    file_stem=card_file_stem,
                    metadata={**card_metadata, "external_render_error": result.get("error")},
                )

            card = {
                "card_index": index,
                "card_type": card_type,
                "headline": slide.get("headline", ""),
                "body": slide.get("body", ""),
                "visual_direction": self._card_visual_direction(card_type),
                "layout_style": self._card_layout_style(card_type),
                "image_prompt": self._normalize_prompt(card_prompt),
                "image_url": result.get("asset_url") if result.get("ok") else None,
                "asset_url": result.get("asset_url") if result.get("ok") else None,
                "asset_id": result.get("asset_id") if result.get("ok") else None,
                "file_path": result.get("file_path") if result.get("ok") else None,
                "mime_type": result.get("mime_type") if result.get("ok") else None,
                "status": "completed" if result.get("ok") else "failed",
                "provider": result.get("provider") or provider_normalized,
                "model": result.get("model") or safe_model,
                "error": result.get("error"),
                "revised_prompt": result.get("revised_prompt"),
                "metadata": result.get("metadata") or {},
            }
            cards.append(card)

        failed_cards = [card for card in cards if card.get("status") != "completed"]

        successful_card = next((card for card in cards if card.get("status") == "completed"), None)
        return {
            "ok": not failed_cards,
            "provider": (successful_card or {}).get("provider") or provider_normalized,
            "model": (successful_card or {}).get("model") or safe_model,
            "cards": cards,
            "size": safe_size,
            "background": safe_background,
            "mime_type": f"image/{safe_output_format}",
            "error": failed_cards[0].get("error") if failed_cards else None,
            "metadata": metadata,
        }

    # -------------------------------------------------------------------------
    # Internal generation
    # -------------------------------------------------------------------------

    def _generate_single_image(
        self,
        *,
        provider: str,
        model: str,
        prompt_original: str,
        prompt_normalized: str,
        prompt_safe_ascii: str,
        size: str,
        background: str,
        output_format: str,
        file_stem: Optional[str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        if provider in {"gemini", "google"}:
            return self._generate_single_image_gemini(
                prompt_original=prompt_original,
                prompt_normalized=prompt_normalized,
                output_format=output_format,
                file_stem=file_stem,
                metadata=metadata,
            )

        if provider != "openai":
            return {
                "ok": False,
                "provider": provider,
                "model": model,
                "error": "unsupported_image_provider",
                "metadata": {
                    **metadata,
                    "prompt_original": prompt_original,
                    "prompt_normalized": prompt_normalized,
                    "prompt_safe_ascii": prompt_safe_ascii,
                },
            }

        if not self.openai_api_key:
            return {
                "ok": False,
                "provider": "openai",
                "model": model,
                "error": "missing_openai_api_key",
                "metadata": {
                    **metadata,
                    "prompt_original": prompt_original,
                    "prompt_normalized": prompt_normalized,
                    "prompt_safe_ascii": prompt_safe_ascii,
                },
            }

        if not str(self.openai_api_key).isascii() or not str(self.openai_api_key).startswith("sk-"):
            return {
                "ok": False,
                "provider": "openai",
                "model": model,
                "error": "invalid_openai_api_key_configuration",
                "metadata": {
                    **metadata,
                    "prompt_original": prompt_original,
                    "prompt_normalized": prompt_normalized,
                    "prompt_safe_ascii": prompt_safe_ascii,
                },
            }

        try:
            from openai import OpenAI
        except Exception as exc:
            return {
                "ok": False,
                "provider": "openai",
                "model": model,
                "error": f"openai_import_failed:{type(exc).__name__}:{exc}",
                "metadata": {
                    **metadata,
                    "prompt_original": prompt_original,
                    "prompt_normalized": prompt_normalized,
                    "prompt_safe_ascii": prompt_safe_ascii,
                },
            }

        try:
            client = OpenAI(api_key=self.openai_api_key)

            self._debug("ABOUT TO CALL OPENAI IMAGES GENERATE")
            self._debug("OPENAI IMAGE MODEL =", model)
            self._debug("OPENAI IMAGE SIZE =", size)

            result = client.images.generate(
                model=model,
                prompt=prompt_safe_ascii,
                size=size,
                background=background,
            )

            data = getattr(result, "data", None) or []
            if not data:
                return {
                    "ok": False,
                    "provider": "openai",
                    "model": model,
                    "error": "image_generation_empty_response",
                    "metadata": {
                        **metadata,
                        "prompt_original": prompt_original,
                        "prompt_normalized": prompt_normalized,
                        "prompt_safe_ascii": prompt_safe_ascii,
                    },
                }

            first = data[0]
            image_b64 = getattr(first, "b64_json", None)
            image_url = getattr(first, "url", None)
            revised_prompt = getattr(result, "revised_prompt", None)

            file_path: Optional[Path] = None
            if image_b64:
                file_path = self._persist_base64_image(
                    b64_json=image_b64,
                    output_format=output_format,
                    file_stem=file_stem,
                    metadata=metadata,
                )

            asset_url = (
                str(file_path)
                if file_path
                else (str(image_url) if image_url else None)
            )

            return {
                "ok": True,
                "provider": "openai",
                "model": model,
                "url": str(image_url) if image_url else None,
                "asset_url": asset_url,
                "asset_id": str(file_path) if file_path else None,
                "b64_json": image_b64,
                "file_path": str(file_path) if file_path else None,
                "mime_type": f"image/{output_format}",
                "revised_prompt": revised_prompt,
                "metadata": {
                    **metadata,
                    "prompt_original": prompt_original,
                    "prompt_normalized": prompt_normalized,
                    "prompt_safe_ascii": prompt_safe_ascii,
                },
            }

        except Exception as exc:
            if self.gemini_api_key and any(
                marker in str(exc).lower()
                for marker in ("insufficient_quota", "credit_balance_exhausted", "no credits remaining")
            ):
                return self._generate_single_image_gemini(
                    prompt_original=prompt_original,
                    prompt_normalized=prompt_normalized,
                    output_format=output_format,
                    file_stem=file_stem,
                    metadata={**metadata, "fallback_from": "openai", "fallback_reason": "insufficient_quota"},
                )
            return {
                "ok": False,
                "provider": "openai",
                "model": model,
                "error": f"image_generation_failed:{type(exc).__name__}:{exc}",
                "metadata": {
                    **metadata,
                    "prompt_original": prompt_original,
                    "prompt_normalized": prompt_normalized,
                    "prompt_safe_ascii": prompt_safe_ascii,
                },
            }

    def _generate_single_image_gemini(
        self,
        *,
        prompt_original: str,
        prompt_normalized: str,
        output_format: str,
        file_stem: Optional[str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        model = os.getenv("AION_GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
        if not self.gemini_api_key:
            return {"ok": False, "provider": "gemini", "model": model, "error": "missing_gemini_api_key", "metadata": metadata}
        endpoint = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt_normalized}]}],
            # The REST API defaults to a 1K image. Some API deployments reject
            # the documented aspect-ratio enum even for supported models, so
            # request the image modality here and crop locally for each channel.
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": str(self.gemini_api_key)},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
            parts = ((((payload.get("candidates") or [{}])[0].get("content") or {}).get("parts")) or [])
            image_part = next((part.get("inlineData") or part.get("inline_data") for part in parts if isinstance(part, dict) and (part.get("inlineData") or part.get("inline_data"))), None)
            image_b64 = (image_part or {}).get("data")
            mime_type = (image_part or {}).get("mimeType") or (image_part or {}).get("mime_type") or "image/png"
            if not image_b64:
                return {"ok": False, "provider": "gemini", "model": model, "error": "gemini_image_generation_empty_response", "metadata": metadata}
            actual_format = "jpeg" if "jpeg" in mime_type else "png"
            file_path = self._persist_base64_image(b64_json=image_b64, output_format=actual_format, file_stem=file_stem, metadata=metadata)
            return {
                "ok": True, "provider": "gemini", "model": model, "url": None,
                "asset_url": str(file_path), "asset_id": str(file_path), "b64_json": None,
                "file_path": str(file_path), "mime_type": mime_type, "revised_prompt": None,
                "metadata": {**metadata, "prompt_original": prompt_original, "prompt_normalized": prompt_normalized},
            }
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            return {"ok": False, "provider": "gemini", "model": model, "error": f"gemini_image_generation_http_{exc.code}:{detail}", "metadata": metadata}
        except Exception as exc:
            return {"ok": False, "provider": "gemini", "model": model, "error": f"gemini_image_generation_failed:{type(exc).__name__}:{exc}", "metadata": metadata}

    def _generate_local_brand_card(
        self,
        *,
        headline: str,
        body: str,
        brand_name: str,
        card_type: str,
        file_stem: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a polished owned fallback when connected render engines have no quota."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            width, height = 1024, 1280
            palettes = {
                "hook": ("#07111f", "#0f766e", "#f8fafc"),
                "problem": ("#111827", "#b45309", "#fff7ed"),
                "solution": ("#082f49", "#0284c7", "#f0f9ff"),
                "proof": ("#14532d", "#16a34a", "#f0fdf4"),
                "cta": ("#1e1b4b", "#7c3aed", "#faf5ff"),
            }
            dark, accent, light = palettes.get(card_type, palettes["hook"])

            def rgb(value: str) -> tuple[int, int, int]:
                value = value.lstrip("#")
                return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

            image = Image.new("RGB", (width, height), rgb(dark))
            draw = ImageDraw.Draw(image)
            accent_rgb = rgb(accent)
            for y in range(height):
                blend = y / max(height - 1, 1)
                base = rgb(dark)
                color = tuple(int(base[i] * (1 - blend * 0.48) + accent_rgb[i] * blend * 0.48) for i in range(3))
                draw.line((0, y, width, y), fill=color)
            panel_fill = tuple(min(255, int(channel * 0.78 + 36)) for channel in rgb(dark))
            draw.rounded_rectangle((65, 62, 959, 1218), radius=34, fill=panel_fill, outline=(255, 255, 255), width=2)
            draw.rectangle((65, 62, 83, 1218), fill=accent_rgb)

            font_candidates = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/SFNS.ttf",
            ]
            def font(size: int, bold: bool = False):
                for candidate in font_candidates:
                    try:
                        return ImageFont.truetype(candidate, size=size)
                    except Exception:
                        continue
                return ImageFont.load_default()

            brand_font = font(32, True)
            headline_font = font(78, True)
            body_font = font(38)
            small_font = font(26, True)
            white = rgb(light)
            draw.text((125, 125), str(brand_name).upper(), font=brand_font, fill=white)
            draw.text((125, 184), f"{card_type.upper()}  ·  HOME IMPROVEMENT", font=small_font, fill=accent_rgb)

            def wrapped(text: str, limit: int) -> list[str]:
                words = str(text or "").split()
                lines: list[str] = []
                current = ""
                for word in words:
                    candidate = f"{current} {word}".strip()
                    if len(candidate) > limit and current:
                        lines.append(current)
                        current = word
                    else:
                        current = candidate
                if current:
                    lines.append(current)
                return lines

            y = 310
            for line in wrapped(headline, 22)[:5]:
                draw.text((125, y), line, font=headline_font, fill=white)
                y += 92
            y += 34
            for line in wrapped(body, 42)[:4]:
                draw.text((125, y), line, font=body_font, fill=white)
                y += 52
            draw.rounded_rectangle((125, 1080, 790, 1152), radius=28, fill=accent_rgb)
            draw.text((163, 1098), "TELL US ABOUT YOUR PROJECT", font=small_font, fill=(255, 255, 255))

            buffer = io.BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            file_path = self._persist_base64_image(
                b64_json=base64.b64encode(buffer.getvalue()).decode("ascii"),
                output_format="png",
                file_stem=file_stem,
                metadata=metadata,
            )
            return {
                "ok": True,
                "provider": "tessaris_local",
                "model": "brand-card-v1",
                "asset_url": str(file_path),
                "asset_id": str(file_path),
                "file_path": str(file_path),
                "mime_type": "image/png",
                "metadata": metadata,
            }
        except Exception as exc:
            return {"ok": False, "provider": "tessaris_local", "model": "brand-card-v1", "error": f"local_brand_card_failed:{type(exc).__name__}:{exc}", "metadata": metadata}

    def _generate_local_evidence_card(
        self,
        *,
        source_path: str,
        headline: str,
        body: str,
        brand_name: str,
        card_type: str,
        file_stem: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Turn an owner-supplied photograph into an owned 4:5 campaign rendition."""
        try:
            from PIL import Image, ImageDraw, ImageEnhance, ImageFont

            width, height = 1024, 1280
            source = Image.open(source_path).convert("RGB")
            scale = max(width / source.width, height / source.height)
            resized = source.resize((int(source.width * scale), int(source.height * scale)), Image.Resampling.LANCZOS)
            left = max(0, (resized.width - width) // 2)
            top = max(0, (resized.height - height) // 2)
            image = resized.crop((left, top, left + width, top + height))
            image = ImageEnhance.Contrast(image).enhance(1.05)
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            for y in range(height):
                alpha = int(35 + (y / height) * 175)
                overlay_draw.line((0, y, width, y), fill=(5, 16, 28, alpha))
            image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(image)
            accent = (15, 118, 110)
            draw.rectangle((0, 0, 18, height), fill=accent)

            def font(size: int):
                for candidate in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/SFNS.ttf"):
                    try:
                        return ImageFont.truetype(candidate, size=size)
                    except Exception:
                        continue
                return ImageFont.load_default()

            def lines(text: str, limit: int) -> list[str]:
                output, current = [], ""
                for word in str(text or "").split():
                    candidate = f"{current} {word}".strip()
                    if current and len(candidate) > limit:
                        output.append(current); current = word
                    else:
                        current = candidate
                if current: output.append(current)
                return output

            draw.text((70, 72), str(brand_name).upper(), font=font(32), fill=(255, 255, 255))
            draw.rounded_rectangle((70, 900, 954, 1210), radius=28, fill=(7, 17, 31))
            y = 940
            for line in lines(headline, 24)[:3]:
                draw.text((112, y), line, font=font(60), fill=(255, 255, 255)); y += 70
            if body:
                y += 10
                for line in lines(body, 48)[:2]:
                    draw.text((112, y), line, font=font(28), fill=(226, 232, 240)); y += 38
            buffer = io.BytesIO(); image.save(buffer, format="PNG", optimize=True)
            file_path = self._persist_base64_image(
                b64_json=base64.b64encode(buffer.getvalue()).decode("ascii"), output_format="png", file_stem=file_stem, metadata=metadata,
            )
            return {
                "ok": True, "provider": "tessaris_owned_media", "model": "evidence-rendition-v1",
                "asset_url": str(file_path), "asset_id": str(file_path), "file_path": str(file_path),
                "mime_type": "image/png", "metadata": {**metadata, "source_path": source_path},
            }
        except Exception as exc:
            return {"ok": False, "provider": "tessaris_owned_media", "model": "evidence-rendition-v1", "error": f"evidence_card_failed:{type(exc).__name__}:{exc}", "metadata": metadata}

    # -------------------------------------------------------------------------
    # Prompt construction for real carousel slides
    # -------------------------------------------------------------------------

    def _build_carousel_card_prompt(
        self,
        *,
        card_index: int,
        card_type: str,
        headline: str,
        body: str,
        caption: str,
        brand_name: Optional[str],
        primary_channel: str,
        offer: Optional[str],
        audience: Optional[str],
        persona: Optional[str],
        objective: Optional[str],
        visual_assets: Dict[str, Any],
    ) -> str:
        card_type_label = card_type.replace("_", " ").strip()
        visual_direction = self._card_visual_direction(card_type)
        layout_style = self._card_layout_style(card_type)
        asset_guidance = self._build_asset_guidance(visual_assets)

        prompt = f"""
Create a polished {primary_channel} carousel slide in portrait social format, designed for a 4:5 style composition.

This is slide {card_index} of a 5-card business marketing carousel.
Brand name: {brand_name or "Local business"}.
Campaign objective: {objective or "Drive local enquiries"}.
Offer: {offer or "Promotional offer"}.
Target audience: {audience or "Local homeowners and small business owners"}.
Persona: {persona or "Local service buyer"}.

Card role: {card_type_label}.
Creative direction: {visual_direction}.
Layout style: {layout_style}.

Important requirements:
- This must look like a finished social carousel slide, not a plain stock image.
- Integrate the slide text INTO the design itself.
- Do not place generic overlay text outside the design system.
- Use strong typography hierarchy, spacing, and premium social-ad composition.
- Keep the design clean, modern, and highly readable on mobile.
- Use realistic business-marketing layout quality.
- Avoid clutter, avoid meme styling, avoid low-quality poster styling.
- Keep wording concise and visually balanced.
- Compose the slide for portrait social use with strong 4:5 visual balance.

Slide text to incorporate into the design:
Headline: {headline or ""}
Supporting text: {body or ""}

Campaign context:
{caption or ""}

Asset guidance:
{asset_guidance}

Style notes:
- best-in-class business carousel design
- editorial / premium social ad feel
- clear storytelling for this card role
- visually distinct from the other cards while staying in the same campaign family
- suitable for Facebook and Instagram carousel usage

Output:
- one finished slide image
- portrait social composition
- fully designed carousel card
""".strip()

        return self._normalize_prompt(prompt)

    def _build_asset_guidance(self, visual_assets: Dict[str, Any]) -> str:
        logo_url = visual_assets.get("logo_url")
        headshot_url = visual_assets.get("headshot_url")
        product_image_urls = visual_assets.get("product_image_urls") or []
        reference_image_urls = visual_assets.get("reference_image_urls") or []

        parts: List[str] = []

        if logo_url:
            parts.append(f"- Logo/reference brand asset available: {logo_url}")
        if headshot_url:
            parts.append(
                f"- Headshot/reference person asset available: {headshot_url}. "
                "If the model/tooling supports it later, incorporate this person naturally."
            )
        if product_image_urls:
            parts.append(
                "- Product/service reference assets available: "
                + ", ".join(str(x) for x in product_image_urls[:5])
            )
        if reference_image_urls:
            parts.append(
                "- Additional creative references available: "
                + ", ".join(str(x) for x in reference_image_urls[:5])
            )

        if not parts:
            return (
                "- No uploaded assets provided. Use a clean, high-end designed business slide "
                "with relevant telecom / connectivity / local service visual storytelling."
            )

        parts.append(
            "- If assets cannot be directly used by the current provider call, still design the slide "
            "as though these assets inform composition and brand direction."
        )
        return "\n".join(parts)

    # -------------------------------------------------------------------------
    # Carousel helpers
    # -------------------------------------------------------------------------

    def _normalize_carousel_slides(
        self,
        carousel: List[Any],
        *,
        caption: str,
    ) -> List[Dict[str, str]]:
        slides: List[Dict[str, str]] = []

        for item in list(carousel or [])[:5]:
            if isinstance(item, str):
                slides.append({"headline": item.strip(), "body": ""})
                continue

            if isinstance(item, dict):
                slides.append(
                    {
                        "headline": str(
                            item.get("headline")
                            or item.get("title")
                            or item.get("hook")
                            or item.get("label")
                            or item.get("text")
                            or ""
                        ).strip(),
                        "body": str(
                            item.get("body")
                            or item.get("subtitle")
                            or item.get("copy")
                            or item.get("description")
                            or item.get("value")
                            or ""
                        ).strip(),
                    }
                )
                continue

            slides.append({"headline": str(item or "").strip(), "body": ""})

        slides = [slide for slide in slides if slide.get("headline") or slide.get("body")]

        if not slides and caption:
            slides = [{"headline": caption.strip(), "body": ""}]

        return slides[:5]

    def _card_type_for_index(self, index: int) -> str:
        if 1 <= index <= len(self.CARD_TYPE_ORDER):
            return self.CARD_TYPE_ORDER[index - 1]
        return "detail"

    @staticmethod
    def _card_visual_direction(card_type: str) -> str:
        directions = {
            "hook": "scroll-stopping promise, premium first impression, striking headline-led composition",
            "problem": "show the pain point clearly, frustration or service problem, strong contrast and tension",
            "solution": "show clear improvement, reliability, modern service, polished and reassuring",
            "proof": "trust-building, local credibility, social proof, confidence and professionalism",
            "cta": "clear action-oriented close, strong conversion intent, clean and decisive layout",
        }
        return directions.get(card_type, "clean business marketing slide")

    @staticmethod
    def _card_layout_style(card_type: str) -> str:
        styles = {
            "hook": "hero headline with premium graphic balance",
            "problem": "pain-point storytelling slide with focused hierarchy",
            "solution": "benefit-led transformation slide",
            "proof": "testimonial / trust / proof-driven slide",
            "cta": "closing offer and action slide",
        }
        return styles.get(card_type, "designed promotional slide")

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def _persist_base64_image(
        self,
        *,
        b64_json: str,
        output_format: str,
        file_stem: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        image_bytes = base64.b64decode(b64_json)
        safe_stem = self._sanitize_file_stem(file_stem or "generated_image")
        safe_format = self._sanitize_output_format(output_format)
        metadata = dict(metadata or {})

        stored_path = self._persist_via_asset_store(
            image_bytes=image_bytes,
            output_format=safe_format,
            file_stem=safe_stem,
            metadata=metadata,
        )
        if stored_path is not None:
            return stored_path

        self.base_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.base_dir / f"{safe_stem}.{safe_format}"
        file_path.write_bytes(image_bytes)
        return file_path

    def _persist_via_asset_store(
        self,
        *,
        image_bytes: bytes,
        output_format: str,
        file_stem: str,
        metadata: Dict[str, Any],
    ) -> Optional[Path]:
        if self.asset_store is None:
            return None

        workspace_id = self._safe_segment(
            metadata.get("workspace_id") or metadata.get("workspace") or "default"
        )
        department_key = self._safe_segment(
            metadata.get("department_key") or "marketing"
        )
        workflow_run_id = self._safe_segment(
            metadata.get("workflow_run_id")
            or metadata.get("run_id")
            or file_stem
        )
        channel = self._safe_segment(
            metadata.get("channel")
            or metadata.get("primary_channel")
            or "general"
        )

        relative_dir = Path("workspaces") / workspace_id / department_key

        if department_key == "marketing":
            relative_dir = relative_dir / "generated_images" / channel / workflow_run_id
        else:
            relative_dir = relative_dir / "generated_images" / workflow_run_id

        filename = f"{file_stem}.{output_format}"

        try:
            if hasattr(self.asset_store, "write_bytes"):
                stored = self.asset_store.write_bytes(
                    relative_path=str(relative_dir / filename),
                    data=image_bytes,
                )
                return Path(stored)

            if hasattr(self.asset_store, "write_binary"):
                stored = self.asset_store.write_binary(
                    relative_path=str(relative_dir / filename),
                    data=image_bytes,
                )
                return Path(stored)

            if hasattr(self.asset_store, "ensure_dir") and hasattr(
                self.asset_store, "resolve_path"
            ):
                self.asset_store.ensure_dir(str(relative_dir))
                resolved = self.asset_store.resolve_path(str(relative_dir / filename))
                path = Path(resolved)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(image_bytes)
                return path

        except Exception:
            return None

        return None

    # -------------------------------------------------------------------------
    # Sanitizers / utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _sanitize_file_stem(value: str) -> str:
        cleaned = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "_"
            for ch in str(value)
        ).strip("_")
        return cleaned or "generated_image"

    @staticmethod
    def _sanitize_output_format(value: str) -> str:
        normalized = str(value or "png").strip().lower()
        allowed = {"png", "jpeg", "jpg", "webp"}
        return normalized if normalized in allowed else "png"

    @staticmethod
    def _safe_segment(value: Any) -> str:
        cleaned = "".join(
            ch if str(ch).isalnum() or ch in {"-", "_"} else "_"
            for ch in str(value or "")
        ).strip("_")
        return cleaned or "default"

    @staticmethod
    def _force_ascii(value: Any) -> str:
        return str(value or "").encode("ascii", "ignore").decode("ascii")

    @staticmethod
    def _normalize_prompt(value: Any) -> str:
        text = str(value or "")

        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u2026": "...",
            "\u00a0": " ",
        }

        for src, dst in replacements.items():
            text = text.replace(src, dst)

        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        return text or "Create a clean, professional social media marketing visual."

    @staticmethod
    def _is_debug_enabled() -> bool:
        value = str(os.getenv("AION_IMAGE_DEBUG", "")).strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _debug(self, *parts: Any) -> None:
        if self._is_debug_enabled():
            print(*parts)
