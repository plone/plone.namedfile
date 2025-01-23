from bs4 import BeautifulSoup
from plone.app.uuid.utils import uuidToObject
from plone.base.interfaces import IImagingSchema
from plone.namedfile.interfaces import IAvailableSizes
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.component import queryUtility

import logging
import re


logger = logging.getLogger(__name__)
appendix_re = re.compile("^(.*)([?#].*)$")
resolveuid_re = re.compile("^[./]*resolve[Uu]id/([^/]*)/?(.*)$")


def get_allowed_scales():
    sizes_util = queryUtility(IAvailableSizes)
    if sizes_util is None:
        return {}
    sizes = sizes_util()
    if sizes is None:
        return {}
    return sizes


def get_picture_variants():
    registry = getUtility(IRegistry)
    settings = registry.forInterface(IImagingSchema, prefix="plone", check=False)
    return getattr(settings, "picture_variants", {})


class Img2PictureTag:
    def get_scale_name(self, scale_line):
        parts = scale_line.split(" ")
        return parts and parts[0] or ""

    def get_scale_width(self, scale):
        """get width from allowed_scales line
        large 800:65536
        """
        allowed_scales = get_allowed_scales()
        scale_info = allowed_scales.get(scale)
        if not scale_info:
            return
        return scale_info[0]

    def create_picture_tag(
        self, sourceset, attributes, uid=None, fieldname=None, resolve_urls=False
    ):
        """Converts the img tag to a picture tag with picture_variant definition"""
        width = None
        height = None
        src = attributes.get("src")
        if not uid and not src:
            raise TypeError("Either uid or attributes['src'] need to be given.")
        soup = BeautifulSoup("", "html.parser")
        allowed_scales = get_allowed_scales()
        if uid:
            obj = uuidToObject(uid, unrestricted=True)
        else:
            obj = self.resolve_uid_url(src)
        picture_tag = soup.new_tag("picture")
        css_classes = attributes.get("class", [])
        if "captioned" in css_classes:
            picture_tag["class"] = "captioned"
        for i, source in enumerate(sourceset):
            target_scale = source["scale"]
            media = source.get("media")

            additional_scales = source.get("additionalScales", None)
            if additional_scales is None:
                additional_scales = [
                    self.get_scale_name(s) for s in allowed_scales if s != target_scale
                ]
            source_scales = [target_scale] + additional_scales
            source_srcset = []
            for scale in source_scales:
                scale_width = self.get_scale_width(scale)
                if not scale_width:
                    logger.warning("No width found for scale %s.", scale)
                    continue
                if resolve_urls and obj:
                    scale_view = obj.unrestrictedTraverse("@@images", None)
                    scale_obj = scale_view.scale(fieldname, scale, pre=True)
                    scale_url = scale_obj.url
                else:
                    # obj = self.resolve_uid_url(src)
                    # scale_view = obj.unrestrictedTraverse("@@images", None)
                    # scale_obj = scale_view.scale(fieldname, scale, pre=True)
                    # scale_url = scale_obj.url
                    scale_url = self.update_src_scale(src=src, scale=scale)
                source_srcset.append(f"{scale_url} {scale_width}w")
            source_tag = soup.new_tag("source", srcset=",\n".join(source_srcset))
            if media:
                source_tag["media"] = media
            picture_tag.append(source_tag)
            if i == len(sourceset) - 1:
                if resolve_urls and obj:
                    scale_view = obj.unrestrictedTraverse("@@images", None)
                    scale_obj = scale_view.scale(fieldname, target_scale, pre=True)
                    scale_url = scale_obj.url
                    width = scale_obj.width
                    height = scale_obj.height
                else:
                    # obj = self.resolve_uid_url(src)
                    # scale_view = obj.unrestrictedTraverse("@@images", None)
                    # scale_obj = scale_view.scale(fieldname, target_scale, pre=True)
                    # scale_url = scale_obj.url
                    # width = scale_obj.width
                    # height = scale_obj.height
                    scale_url = self.update_src_scale(src=src, scale=target_scale)
                img_tag = soup.new_tag("img", src=scale_url)
                for k, attr in attributes.items():
                    if k in ["src", "srcset"]:
                        continue
                    img_tag.attrs[k] = attr
                img_tag["loading"] = "lazy"
                if width:
                    img_tag["width"] = width
                if height:
                    img_tag["height"] = height
                picture_tag.append(img_tag)
        return picture_tag

    def resolve_uid_url(self, href):
        obj = None
        subpath = href
        match = resolveuid_re.match(subpath)
        if match is not None:
            uid, _subpath = match.groups()
            obj = uuidToObject(uid, unrestricted=True)
        return obj

    def update_src_scale(self, src, scale):
        parts = src.split("/")
        if "." in parts[-1]:
            field_name = parts[-1].split("-")[0]
            src_scale = "/".join(parts[:-1]) + f"/{field_name}/{scale}"
            src_scale
        else:
            # Usually the url has '@@images/fieldname/other_scale',
            # and then we replace the other scale.
            # But the url may use the original image, e.g. @@images/image.
            # Then we want to keep the fieldname and return '.../image/scale'.
            try:
                full = len(parts) - parts.index("@@images") == 2
            except ValueError:
                full = False
            if not full:
                parts = parts[:-1]
            src_scale = "/".join(parts) + f"/{scale}"
        return src_scale
