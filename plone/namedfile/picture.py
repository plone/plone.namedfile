import logging
import re

from plone.base.interfaces import IImagingSchema
from plone.outputfilters.browser.resolveuid import uuidToObject
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from bs4 import BeautifulSoup

logger = logging.getLogger("plone.outputfilter.image_srcset")
appendix_re = re.compile('^(.*)([?#].*)$')
resolveuid_re = re.compile('^[./]*resolve[Uu]id/([^/]*)/?(.*)$')


class Img2PictureTag(object):
    @property
    def allowed_scales(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IImagingSchema, prefix="plone", check=False)
        return settings.allowed_sizes

    @property
    def image_srcsets(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IImagingSchema, prefix="plone", check=False)
        return settings.image_srcsets

    def get_scale_name(self, scale_line):
        parts = scale_line.split(" ")
        return parts and parts[0] or ""

    def get_scale_width(self, scale):
        """get width from allowed_scales line
        large 800:65536
        """
        for s in self.allowed_scales:
            parts = s.split(" ")
            if not parts:
                continue
            if parts[0] == scale:
                dimentions = parts[1].split(":")
                if not dimentions:
                    continue
                return dimentions[0]

    def create_picture_tag(self, sourceset, attributes, uid=None, fieldname=None, resolve_urls=False):
        """Converts the img tag to a picture tag with srcset definition"""
        src = attributes.get("src")
        if not uid and not src:
            raise TypeError("Either uid or attributes['src'] need to be given.")
        soup = BeautifulSoup("", "html.parser")
        allowed_scales = self.allowed_scales
        if uid:
            obj = uuidToObject(uid)
        else:
            obj = self.resolve_uid_url(src)
        picture_tag = soup.new_tag("picture")
        css_classes = attributes.get("class")
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
                if resolve_urls and obj:
                    scale_view = obj.unrestrictedTraverse('@@images', None)
                    scale_obj = scale_view.scale(fieldname, scale, pre=True)
                    scale_url = scale_obj.url
                elif src:
                    scale_url = self.update_src_scale(src=src, scale=scale)
                scale_width = self.get_scale_width(scale)
                source_srcset.append("{0} {1}w".format(scale_url, scale_width))
            source_tag = soup.new_tag("source", srcset=",\n".join(source_srcset))
            if media:
                source_tag["media"] = media
            picture_tag.append(source_tag)
            if i == len(sourceset) - 1:
                scale_view = obj.unrestrictedTraverse('@@images', None)
                scale_obj = scale_view.scale(fieldname, target_scale, pre=True)
                scale_url = scale_obj.url
                img_tag = soup.new_tag(
                    "img",
                    src=self.update_src_scale(src=scale_url, scale=target_scale),
                )
                for k, attr in attributes.items():
                    if k in ["src", "srcset"]:
                        continue
                    img_tag.attrs[k] = attr
                img_tag["loading"] = "lazy"
                picture_tag.append(img_tag)
        return picture_tag

    def resolve_uid_url(self, href):
        obj = None
        subpath = href
        match = resolveuid_re.match(subpath)
        if match is not None:
            uid, _subpath = match.groups()
            obj = uuidToObject(uid)
        return obj

    def update_src_scale(self, src, scale):
        parts = src.split("/")
        if "." in parts[-1]:
            field_name = parts[-1].split("-")[0]
            src_scale =  "/".join(parts[:-1]) + "/{0}/{1}".format(field_name, scale)
            src_scale
        else:
            src_scale = "/".join(parts[:-1]) + "/{}".format(scale)
        print(src_scale)
        return src_scale
