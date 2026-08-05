#!/usr/bin/env python3
"""Repair the uploaded Creative Soil Framer static export in place.

This script intentionally operates only on /home/ubuntu/creative-soil-test-upload/build.
It does not read from, write to, commit to, or deploy the production Creative Soil project.
"""

from __future__ import annotations

import json
import re
from copy import copy
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment


ROOT = Path("/home/ubuntu/creative-soil-test-upload/build")
REFERENCE_ROOT = Path("/home/ubuntu/creativesoil-reference")
SOURCE_ORIGIN = "https://creativesoil.framer.website"
TEST_ORIGIN = "https://test3-liza-2565s-projects.vercel.app"
REPORT_PATH = ROOT.parent / "repair_report.json"

FONT_URL_RE = re.compile(
    r"url\(\s*(?P<quote>[\"']?)(?:(?:\.\.?/)+)fonts/(?P<path>[^\"')]+)(?P=quote)\s*\)",
    flags=re.IGNORECASE,
)
IMAGE_URL_RE = re.compile(
    r"url\(\s*(?P<quote>[\"']?)(?:(?:\.\.?/)+)images/(?P<path>[^\"')]+)(?P=quote)\s*\)",
    flags=re.IGNORECASE,
)
RELATIVE_IMAGE_ATTR_RE = re.compile(
    r"(?P<prefix>\b(?:src|href|poster|data-src)=[\"'])(?:(?:\.\.?/)+)images/",
    flags=re.IGNORECASE,
)
EXTERNAL_WOFF2_RE = re.compile(
    r"https?://[^\"')\s]+/(?P<filename>[^/?\"')\s]+\.woff2)(?:\?[^\"')\s]*)?",
    flags=re.IGNORECASE,
)

ENCODING_REPAIRS = {
    "Â£": "£",
    "Â©": "©",
    "â": "’",
    "â": "—",
    "â": "–",
    "â¦": "…",
    "â€¢": "•",
}

BRAND_COLOUR_REPAIRS = {
    "rgb(6, 61, 48)": "rgb(31, 54, 62)",
    "rgb(6,61,48)": "rgb(31,54,62)",
    "rgba(6, 61, 48,": "rgba(31, 54, 62,",
    "rgba(6,61,48,": "rgba(31,54,62,",
    "#063d30": "#1f363e",
    "#063D30": "#1F363E",
}

HOMEPAGE_HERO_LINKS = {"#hero", "./#hero", "../#hero", "/#hero"}


STATIC_PROTECTION_CSS = r"""
/* Creative Soil static test export: remove Framer promotional/editor UI and
   provide self-contained typography and entrance effects without external runtime. */
#__framer-badge-container,
.__framer-badge,
#__framer-editorbar-container,
#__framer-editorbar,
#__framer-editorbar-button,
#__framer-editorbar-label,
a[href^="https://framer.link/"],
a[href="https://www.framer.com"] {
    display: none !important;
}
/* The source supplies Anton through a Framer-hosted face. Give it a unique,
   local identity so every intended Anton preset uses the verified Anton
   Regular file rather than a browser fallback or an ambiguous alias. */
@font-face {
    font-family: "Creative Soil Anton Regular";
    src: url("/fonts/PCXT6E5YCQO6SSVLT6UZPPGT7QKGXOUS_ce309f94.woff2") format("woff2");
    font-style: normal;
    font-weight: 400;
    font-display: swap;
}
.framer-styles-preset-15avxz5,
.framer-styles-preset-15ncy3i,
.framer-styles-preset-1lpq4wh,
.framer-styles-preset-4cp3fc {
    --framer-font-family: "Creative Soil Anton Regular", "Anton", sans-serif !important;
    --framer-font-family-bold: "Creative Soil Anton Regular", "Anton", sans-serif !important;
    --framer-font-family-bold-italic: "Creative Soil Anton Regular", "Anton", sans-serif !important;
    --framer-font-family-italic: "Creative Soil Anton Regular", "Anton", sans-serif !important;
    --framer-font-weight: 400 !important;
    --framer-font-style: normal !important;
    font-family: "Creative Soil Anton Regular", "Anton", sans-serif !important;
    font-weight: 400 !important;
    font-style: normal !important;
    font-synthesis: none;
}
/* Preserve a visible static fallback. The local animator explicitly marks its
   own elements before applying their authored initial states. */
[data-framer-appear-id]:not([data-creative-soil-animated]),
[style*="opacity: 0.001"]:not([data-creative-soil-animated]) {
    opacity: 1 !important;
}
/* When the self-contained word reveal is active, retain Framer's authored
   hidden/blurred starting state until the script transitions every word to a
   permanently sharp final state. Without JavaScript, the fallback above keeps
   the text visible rather than leaving the page blank. */
html[data-creative-soil-text-reveal-active="true"] span[style*="filter: blur"],
html[data-creative-soil-text-reveal-active="true"] span[style*="filter:blur"] {
    opacity: 0.001 !important;
}
""".strip()

LEGAL_BULLET_CSS = r"""
#main ul.framer-text {
    list-style: none !important;
}
#main ul.framer-text > li {
    position: relative !important;
}
#main ul.framer-text > li::before {
    content: "•" !important;
    font-family: Arial, sans-serif !important;
    position: absolute !important;
    left: -1.05em !important;
    top: 0 !important;
}
""".strip()

# This client-side scrubber protects against any late Framer hydration that might
# add an editor bar, badge, template CTA, old colours, or a /#hero URL again.
RUNTIME_SANITIZER = r"""(()=>{
const sourceHost="creativesoil."+"framer.website";
const sourceOrigin="https://"+sourceHost;
const testOrigin="https://test3-liza-2565s-projects.vercel.app";
const oldYear="20"+"25",newYear="20"+"26";
const recolor=value=>(value||"")
  .replaceAll("rgb("+"6, 61, 48)","rgb(31, 54, 62)")
  .replaceAll("rgb("+"6,61,48)","rgb(31,54,62)")
  .replaceAll("rgba("+"6, 61, 48,","rgba(31, 54, 62,")
  .replaceAll("rgba("+"6,61,48,","rgba(31,54,62,")
  .replaceAll("#"+"063d30","#1f363e")
  .replaceAll("#"+"063D30","#1F363E");
const cleanup=()=>{
  document.querySelectorAll("#__framer-badge-container,.__framer-badge,#__framer-editorbar-container,#__framer-editorbar,#__framer-editorbar-button,#__framer-editorbar-label").forEach(el=>(el.closest("#__framer-badge-container,#__framer-editorbar-container")||el).remove());
  document.querySelectorAll('a[href^="https://framer.link/"],a[href="https://www.framer.com"]').forEach(a=>(a.closest('div[class*="-container"]')||a).remove());
  document.querySelectorAll("[data-framer-appear-id]:not([data-creative-soil-animated])").forEach(el=>{if(el.style.opacity!=="1")el.style.setProperty("opacity","1","important")});
  document.querySelectorAll("style").forEach(style=>{const value=style.textContent||"";const next=recolor(value);if(next!==value)style.textContent=next});
  document.querySelectorAll("[style]").forEach(el=>{const value=el.getAttribute("style")||"";const next=recolor(value);if(next!==value)el.setAttribute("style",next)});
  document.querySelectorAll("[fill],[stroke]").forEach(el=>["fill","stroke"].forEach(attr=>{if(!el.hasAttribute(attr))return;const value=el.getAttribute(attr)||"";const next=recolor(value);if(next!==value)el.setAttribute(attr,next)}));
  document.querySelectorAll("time").forEach(time=>{if((time.textContent||"").includes(oldYear))time.textContent=time.textContent.replaceAll(oldYear,newYear);if((time.getAttribute("datetime")||"").includes(oldYear))time.setAttribute("datetime",time.getAttribute("datetime").replaceAll(oldYear,newYear))});
  document.querySelectorAll("a[href]").forEach(a=>{const href=a.getAttribute("href")||"";const text=(a.textContent||"").trim();if(href.startsWith(sourceOrigin)){a.setAttribute("href",href.replace(sourceOrigin,testOrigin));return}if(["#hero","./#hero","../#hero","/#hero"].includes(href)){a.setAttribute("href","/");return}if(text==="hello@creativesoil.co")a.setAttribute("href","mailto:hello@creativesoil.co");if(text==="+44 7542 866885")a.setAttribute("href","tel:+447542866885")});
  if(location.pathname==="/"&&location.hash==="#hero")history.replaceState(null,"",location.pathname+location.search);
};
document.addEventListener("DOMContentLoaded",cleanup,{once:true});
window.addEventListener("hashchange",cleanup);
[0,100,500,1500].forEach(delay=>setTimeout(cleanup,delay));
cleanup();
})();"""

# Recreates the four original Framer entrance effects locally. It retains the
# source timing, translations and rotations while avoiding the external Framer
# runtime that could otherwise leave the static export blank.
STATIC_APPEAR_ANIMATOR = r"""(()=>{
const effects={
  "14q8xyt":{y:-88,delay:1000,duration:1600},
  "8d49vl":{y:10,delay:800,duration:1600},
  "xhi78j":{y:20,delay:800,duration:1600},
  "1wetvay":{y:20,delay:800,duration:1600}
};
const ease="cubic-bezier(.22,1,.36,1)";
const reveal=()=>{
  if(document.documentElement.dataset.creativeSoilAppearStarted)return;
  document.documentElement.dataset.creativeSoilAppearStarted="true";
  const reduced=window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const entries=[];
  document.querySelectorAll("[data-framer-appear-id]").forEach(el=>{
    const effect=effects[el.getAttribute("data-framer-appear-id")];
    if(!effect)return;
    const base=(el.style.transform||"none").trim();
    el.setAttribute("data-creative-soil-animated","true");
    if(reduced){
      el.style.setProperty("opacity","1","important");
      return;
    }
    entries.push({el,effect,base});
    el.style.setProperty("will-change","opacity, transform");
    el.style.setProperty("transition","none");
    el.style.setProperty("transition-delay","0ms");
    el.style.setProperty("opacity","0.001","important");
    el.style.setProperty("transform",`${base==="none"?"":base} translateY(${effect.y}px)`.trim());
  });
  requestAnimationFrame(()=>requestAnimationFrame(()=>entries.forEach(({el,effect,base})=>{
    el.style.setProperty("transition",`opacity ${effect.duration}ms ${ease}, transform ${effect.duration}ms ${ease}`);
    el.style.setProperty("transition-delay",`${effect.delay}ms`);
    el.style.setProperty("opacity","1","important");
    el.style.setProperty("transform",base);
    window.setTimeout(()=>{
      el.style.removeProperty("will-change");
      el.style.removeProperty("transition");
      el.style.removeProperty("transition-delay");
    },effect.delay+effect.duration+120);
  })));
};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",reveal,{once:true});else reveal();
})();"""

# Framer's rich-text runtime also animates hundreds of individually styled word
# spans. The exported markup retains their initial opacity, blur and translateY
# values, while the runtime that would finish them is removed for static safety.
# This lightweight replacement observes each word group when it enters view,
# then transitions it to an explicitly sharp, visible final state.
STATIC_TEXT_REVEAL_ANIMATOR = r"""(()=>{
const selector='span[style*="filter: blur"],span[style*="filter:blur"]';
const duration=720,stagger=36,ease='cubic-bezier(.22,1,.36,1)';
document.documentElement.dataset.creativeSoilTextRevealActive='true';
const finalize=node=>{
  node.style.setProperty('opacity','1','important');
  node.style.setProperty('filter','none','important');
  node.style.setProperty('transform','none','important');
  node.style.removeProperty('will-change');
  node.style.removeProperty('transition');
  node.style.removeProperty('transition-delay');
  node.setAttribute('data-creative-soil-text-revealed','true');
};
const revealGroup=nodes=>{
  if(!nodes.length||nodes[0].dataset.creativeSoilTextRevealStarted)return;
  nodes.forEach(node=>{
    node.dataset.creativeSoilTextRevealStarted='true';
    node.setAttribute('data-creative-soil-animated','true');
  });
  const reduced=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(reduced){nodes.forEach(finalize);return;}
  nodes.forEach(node=>{
    node.style.setProperty('will-change','opacity, filter, transform');
    node.style.setProperty('transition','none');
    node.style.setProperty('transition-delay','0ms');
    node.style.setProperty('opacity','0.001','important');
    node.style.setProperty('filter','blur(10px)','important');
    if(!node.style.transform||node.style.transform==='none')node.style.setProperty('transform','translateY(10px)','important');
  });
  requestAnimationFrame(()=>requestAnimationFrame(()=>nodes.forEach((node,index)=>{
    const delay=index*stagger;
    node.style.setProperty('transition',`opacity ${duration}ms ${ease}, filter ${duration}ms ${ease}, transform ${duration}ms ${ease}`);
    node.style.setProperty('transition-delay',`${delay}ms`);
    node.style.setProperty('opacity','1','important');
    node.style.setProperty('filter','none','important');
    node.style.setProperty('transform','none','important');
    window.setTimeout(()=>finalize(node),duration+delay+80);
  })));
};
const start=()=>{
  const groups=new Map();
  document.querySelectorAll(selector).forEach(node=>{
    const parent=node.parentElement;
    if(!parent)return;
    const list=groups.get(parent)||[];
    list.push(node);
    groups.set(parent,list);
  });
  const reduced=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(reduced){groups.forEach(revealGroup);return;}
  if(!('IntersectionObserver' in window)){groups.forEach(revealGroup);return;}
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
    if(entry.isIntersecting){
      revealGroup(groups.get(entry.target)||[]);
      observer.unobserve(entry.target);
    }
  }),{threshold:.08,rootMargin:'0px 0px -6% 0px'});
  groups.forEach((_,parent)=>observer.observe(parent));
};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();"""



# The exported Framer document has the visual markup for these interactions but
# relies on the removed runtime for state management. This small, local runtime
# restores only the site behaviours needed by the static test export.
STATIC_INTERACTION_RUNTIME = r"""(()=>{
const routeMap=[
  [/\/contac(?=\/|$)/gi,'/contact'],
  [/\/works\/fa(?=\/|$)/gi,'/works/fatt'],
  [/\/works\/roa(?=\/|$)/gi,'/works/roam'],
  [/\/works\/recla(?=\/|$)/gi,'/works/reclaim'],
  [/\/ideas\/the-harrods-halo-effect-the-secret-listing-that-will-transform-your-entire-food-bra(?=\/|$)/gi,'/ideas/the-harrods-halo-effect-the-secret-listing-that-will-transform-your-entire-food-brand'],
  [/\/ideas\/are-you-burning-cash-on-digital-ads-while-your-competitors-scale-for-fr(?=\/|$)/gi,'/ideas/are-you-burning-cash-on-digital-ads-while-your-competitors-scale-for-free'],
  [/\/ideas\/the-brutal-reason-your-wellness-drink-is-dying-on-the-shelf\.(?=\/|$)/gi,'/ideas/the-brutal-reason-your-wellness-drink-is-dying-on-the-shelf'],
  [/\/ideas\/([^/]+)\.(?=\/?$)/gi,'/ideas/$1']
];
const normalizeHref=raw=>{
  if(!raw||raw.startsWith('#')||/^(mailto:|tel:|javascript:|data:)/i.test(raw))return raw;
  let url;
  try{url=new URL(raw,location.href)}catch{return raw}
  if(url.origin!==location.origin)return raw;
  let path=url.pathname;
  routeMap.forEach(([pattern,replacement])=>{path=path.replace(pattern,replacement)});
  return path+url.search+url.hash;
};
const repairLinks=(root=document)=>root.querySelectorAll('a[href]').forEach(anchor=>{
  const current=anchor.getAttribute('href')||'';
  const next=normalizeHref(current);
  if(next!==current)anchor.setAttribute('href',next);
});
	const makeInteractive=(element,action)=>{
	  if(!element||element.dataset.creativeSoilInteractive==='true')return;
	  element.dataset.creativeSoilInteractive='true';
	  element.setAttribute('role','button');
	  element.setAttribute('tabindex','0');
	  const activate=event=>{
	    if(event){
	      event.preventDefault();
	      event.stopPropagation();
	      if(typeof event.stopImmediatePropagation==='function')event.stopImmediatePropagation();
	    }
	    action(event);
	  };
	  element.addEventListener('click',activate,true);
	  element.addEventListener('keydown',event=>{
	    if(event.key==='Enter'||event.key===' '){activate(event)}
	  },true);
	};
	const installInteractionStyles=()=>{
	  if(document.getElementById('creative-soil-static-interaction-styles'))return;
	  const style=document.createElement('style');
	  style.id='creative-soil-static-interaction-styles';
	  style.textContent=`
    /* FAQ: preserve each question as a dark card with a deliberate + / × control.
       The export's original animated answer wrapper collapses to 1px, so make all
       content layers normal-width blocks when a card opens. */
    [data-framer-name="Q & A"]{cursor:default!important;width:100%!important;min-width:0!important;box-sizing:border-box!important;}
    [data-framer-name="Q & A"] [data-framer-name="Question"]{position:relative!important;display:flex!important;align-items:center!important;width:100%!important;min-width:0!important;box-sizing:border-box!important;padding-right:82px!important;}
    [data-framer-name="Q & A"] [data-framer-name="Question"] > :first-child{display:block!important;flex:1 1 auto!important;min-width:0!important;width:auto!important;}
    [data-framer-name="Q & A"][data-creative-soil-faq-open="true"]{width:100%!important;min-width:0!important;flex:0 0 auto!important;height:auto!important;max-height:none!important;align-items:stretch!important;overflow:visible!important;}
    [data-framer-name="Q & A"] [data-creative-soil-faq-answer="true"]{position:static!important;display:block!important;visibility:visible!important;width:100%!important;min-width:0!important;flex:0 0 auto!important;box-sizing:border-box!important;overflow:hidden!important;}
    [data-framer-name="Q & A"] [data-creative-soil-faq-answer="true"] > *{display:block!important;visibility:visible!important;width:100%!important;max-width:none!important;min-width:0!important;flex:0 0 auto!important;box-sizing:border-box!important;}
    [data-framer-name="Q & A"] [data-creative-soil-faq-answer="true"] p{display:block!important;visibility:visible!important;width:100%!important;max-width:none!important;min-width:0!important;box-sizing:border-box!important;white-space:normal!important;word-break:normal!important;overflow-wrap:break-word!important;writing-mode:horizontal-tb!important;text-orientation:mixed!important;}
    [data-framer-name="Closed"]{position:relative!important;}
    .creative-soil-faq-toggle{position:absolute!important;z-index:5!important;right:24px!important;top:20px!important;display:grid!important;place-items:center!important;width:44px!important;height:44px!important;margin:0!important;padding:0!important;transform:none!important;border:2px solid rgb(239,239,239)!important;border-radius:10px!important;background:transparent!important;color:rgb(239,239,239)!important;font:400 32px/1 Arial,sans-serif!important;cursor:pointer!important;}
    [data-framer-name="Closed"]:has([data-framer-name="Q & A"][data-creative-soil-faq-open="true"]) .creative-soil-faq-toggle{border-color:#F5D636!important;background:#F5D636!important;color:#1F363E!important;}
    /* Article CTA: make the complete Works-style contact action visible on article pages. */
    section[data-framer-name="CTA Section"]{position:relative!important;min-height:430px!important;overflow:hidden!important;}
    section[data-framer-name="CTA Section"] .creative-soil-article-cta-link{position:relative!important;z-index:2!important;display:inline-flex!important;align-items:center!important;gap:16px!important;max-width:48%!important;text-decoration:none!important;color:#1F363E!important;font:400 clamp(52px,5.4vw,80px)/1 "Anton",Arial,sans-serif!important;letter-spacing:0!important;}
    section[data-framer-name="CTA Section"] .creative-soil-article-cta-arrow{display:inline-grid!important;place-items:center!important;width:36px!important;height:36px!important;flex:0 0 36px!important;border:1.5px solid #1F363E!important;border-radius:8px!important;color:#1F363E!important;font:600 22px/1 Arial,sans-serif!important;}
    .creative-soil-article-cta-media{position:absolute!important;z-index:1!important;right:8%!important;top:50%!important;width:min(38vw,480px)!important;height:280px!important;transform:translateY(-50%)!important;pointer-events:none!important;}
    .creative-soil-article-cta-media img{position:absolute!important;display:block!important;width:72%!important;height:82%!important;object-fit:cover!important;border:2px solid #1F363E!important;border-radius:28px!important;background:#1F363E!important;box-shadow:none!important;}
    .creative-soil-article-cta-media img:nth-child(1){left:0!important;bottom:4px!important;opacity:.34!important;transform:translate(-18px,18px)!important;}
    .creative-soil-article-cta-media img:nth-child(2){left:9%!important;bottom:9px!important;opacity:.62!important;transform:translate(-4px,8px)!important;}
    .creative-soil-article-cta-media img:nth-child(3){right:0!important;bottom:20px!important;width:86%!important;height:92%!important;opacity:1!important;transform:none!important;}
    /* Contact header Works link: a durable pill positioned alongside the hydrated native tabs. */
    #creative-soil-contact-works-link{position:fixed!important;z-index:2147483000!important;display:grid!important;place-items:center!important;min-width:64px!important;height:40px!important;box-sizing:border-box!important;padding:8px 12px!important;overflow:hidden!important;border-radius:120px!important;background:var(--token-cdfc1154-0600-4560-a58f-23c5d7362a76,#fafafa)!important;color:#1F363E!important;text-decoration:none!important;font:500 16px/1.2 Satoshi,Arial,sans-serif!important;letter-spacing:-.02em!important;cursor:pointer!important;isolation:isolate!important;}
    #creative-soil-contact-works-link .creative-soil-works-label{position:relative!important;display:block!important;line-height:1.2!important;transition:transform .28s cubic-bezier(.22,1,.36,1)!important;}
    #creative-soil-contact-works-link .creative-soil-works-label::after{content:"Works"!important;position:absolute!important;left:0!important;top:100%!important;color:#F5D636!important;white-space:nowrap!important;}
    #creative-soil-contact-works-link::after{content:""!important;position:absolute!important;left:50%!important;bottom:5px!important;width:18px!important;height:2px!important;transform:translateX(-50%) scaleX(0)!important;transform-origin:center!important;background:#F5D636!important;border-radius:4px!important;transition:transform .28s cubic-bezier(.22,1,.36,1)!important;}
    #creative-soil-contact-works-link:hover .creative-soil-works-label,#creative-soil-contact-works-link:focus-visible .creative-soil-works-label{transform:translateY(-100%)!important;}
    #creative-soil-contact-works-link:hover::after,#creative-soil-contact-works-link:focus-visible::after{transform:translateX(-50%) scaleX(1)!important;}
    #creative-soil-contact-works-link:focus-visible{outline:2px solid #F5D636!important;outline-offset:3px!important;}
    /* Pricing CTA: retain the full card-width yellow rounded pill from the original design. */
    [data-framer-name="Plans Cards"] .creative-soil-plan-cta{display:block!important;box-sizing:border-box!important;width:100%!important;min-width:0!important;margin-top:8px!important;}
    [data-framer-name="Plans Cards"] .creative-soil-plan-cta a{display:flex!important;box-sizing:border-box!important;width:100%!important;min-width:0!important;max-width:none!important;min-height:52px!important;align-items:center!important;justify-content:center!important;border:1px solid #1F363E!important;border-radius:455px!important;background:#F5D636!important;color:#1F363E!important;white-space:nowrap!important;word-break:normal!important;overflow-wrap:normal!important;writing-mode:horizontal-tb!important;text-orientation:mixed!important;text-align:center!important;font:700 18px/1 Satoshi,Arial,sans-serif!important;padding:14px 28px!important;}
    [data-framer-name="Plans Cards"] .creative-soil-plan-cta a *{display:inline!important;color:inherit!important;white-space:nowrap!important;word-break:normal!important;overflow-wrap:normal!important;writing-mode:horizontal-tb!important;text-orientation:mixed!important;line-height:1!important;}
    /* Article recommendations: make the exported three cards visible and form a desktop grid. */
    section[data-framer-name="More Projects"] [data-framer-name="Blog Cards"]{width:100%!important;min-width:0!important;}
    section[data-framer-name="More Projects"] [data-framer-name="Blog Cards"] .framer-n9hjcv{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:20px!important;width:100%!important;min-width:0!important;align-items:stretch!important;}
    section[data-framer-name="More Projects"] [data-framer-name="Blog Cards"] .ssr-variant{display:block!important;width:100%!important;min-width:0!important;height:auto!important;}
    section[data-framer-name="More Projects"] [data-framer-name="Blog Cards"] .framer-1ft8x8m-container{display:block!important;width:100%!important;min-width:0!important;height:auto!important;opacity:1!important;transform:none!important;will-change:auto!important;}
    section[data-framer-name="More Projects"] [data-framer-name="Blog Cards"] a[href]{display:flex!important;width:100%!important;min-width:0!important;height:100%!important;box-sizing:border-box!important;opacity:1!important;visibility:visible!important;}
    /* Replace the exported decorative search label with one functional search field. */
    [data-framer-name="Search Input"][data-creative-soil-search-ready="true"]{position:relative!important;display:flex!important;align-items:center!important;width:100%!important;min-width:0!important;box-sizing:border-box!important;padding:0 16px!important;}
    [data-framer-name="Search Input"] .creative-soil-search-icon{flex:0 0 auto!important;display:inline-block!important;margin-right:10px!important;color:rgba(2,2,2,.62)!important;font:22px/1 Arial,sans-serif!important;pointer-events:none!important;}
    [data-framer-name="Search Input"] .creative-soil-ideas-search{position:static!important;z-index:auto!important;flex:1 1 auto!important;display:block!important;width:100%!important;min-width:0!important;height:100%!important;min-height:44px!important;padding:0!important;border:0!important;outline:0!important;background:transparent!important;color:inherit!important;font:inherit!important;line-height:1.25!important;}
    [data-framer-name="Search Input"] .creative-soil-ideas-search::placeholder{color:rgba(2,2,2,.62)!important;opacity:1!important;}
    @media (max-width:820px){
      section[data-framer-name="More Projects"] [data-framer-name="Blog Cards"] .framer-n9hjcv{grid-template-columns:1fr!important;gap:18px!important;}
      section[data-framer-name="CTA Section"]{min-height:0!important;overflow:visible!important;}
      section[data-framer-name="CTA Section"] .creative-soil-article-cta-link{max-width:100%!important;font-size:54px!important;}
      .creative-soil-article-cta-media{position:relative!important;right:auto!important;top:auto!important;width:min(100%,440px)!important;height:230px!important;margin:38px auto 0!important;transform:none!important;}
    }

	  `;
	  document.head.append(style);
	};

		const initFaq=()=>{
		  const cards=[...document.querySelectorAll('[data-framer-name="Q & A"]')];
		  const applyState=(card,open)=>{
		    const question=card.querySelector('[data-framer-name="Question"]');
		    const answer=card.querySelector('[data-framer-name="Answer"]');
		    const shell=card.closest('[data-framer-name="Closed"]')||card;
		    const toggle=shell.querySelector('.creative-soil-faq-toggle');
		    if(!question||!answer)return;
		    card.dataset.creativeSoilFaqOpen=open?'true':'false';
		    question.setAttribute('aria-expanded',String(open));
		    answer.dataset.creativeSoilFaqAnswer='true';
		    card.classList.toggle('framer-v-3ee1h7',open);
		    if(toggle){
		      toggle.textContent=open?'×':'+';
		      toggle.setAttribute('aria-label',open?'Close answer':'Open answer');
		      toggle.setAttribute('aria-expanded',String(open));
		      toggle.style.setProperty('border-color',open?'#F5D636':'rgb(239,239,239)','important');
		      toggle.style.setProperty('background',open?'#F5D636':'transparent','important');
		      toggle.style.setProperty('color',open?'#1F363E':'rgb(239,239,239)','important');
		    }
		    card.style.setProperty('overflow',open?'visible':'hidden','important');
		    answer.style.setProperty('display','block','important');
		    answer.style.setProperty('visibility','visible','important');
		    answer.style.setProperty('position','static','important');
		    answer.style.setProperty('top','auto','important');
		    answer.style.setProperty('left','auto','important');
		    answer.style.setProperty('width','100%','important');
		    answer.style.setProperty('height','auto','important');
		    answer.style.setProperty('min-height','0','important');
		    answer.style.setProperty('box-sizing','border-box','important');
		    answer.style.setProperty('overflow','hidden','important');
		    answer.style.setProperty('transition','max-height 360ms cubic-bezier(.22,1,.36,1), opacity 220ms ease, margin-top 360ms cubic-bezier(.22,1,.36,1)','important');
		    answer.querySelectorAll('*').forEach(node=>{
		      node.style.setProperty('display','block','important');
		      node.style.setProperty('visibility','visible','important');
		      node.style.setProperty('position','static','important');
		      node.style.setProperty('width','100%','important');
		      node.style.setProperty('max-width','none','important');
		      node.style.setProperty('min-width','0','important');
		      node.style.setProperty('box-sizing','border-box','important');
		      node.style.setProperty('white-space','normal','important');
		      node.style.setProperty('word-break','normal','important');
		      node.style.setProperty('overflow-wrap','break-word','important');
		      node.style.setProperty('writing-mode','horizontal-tb','important');
		      node.style.setProperty('text-orientation','mixed','important');
		      node.style.setProperty('filter','none','important');
		      node.style.setProperty('transform','none','important');
		      node.style.setProperty('opacity','1','important');
		    });
		    if(open){
		      card.style.setProperty('width','100%','important');
		      card.style.setProperty('height','auto','important');
		      card.style.setProperty('max-height','none','important');
		      answer.style.setProperty('opacity','1','important');
		      answer.style.setProperty('max-height','1600px','important');
		      answer.style.setProperty('margin-top','0','important');
		    }else{
		      card.style.removeProperty('width');
		      card.style.removeProperty('height');
		      card.style.removeProperty('max-height');
		      answer.style.setProperty('opacity','0','important');
		      answer.style.setProperty('max-height','0px','important');
		      answer.style.setProperty('margin-top','0','important');
		    }
		  };
		  cards.forEach(card=>{
		    const question=card.querySelector('[data-framer-name="Question"]');
		    const answer=card.querySelector('[data-framer-name="Answer"]');
		    if(!question||!answer)return;
		    const shell=card.closest('[data-framer-name="Closed"]')||card;
		    shell.querySelectorAll('[data-framer-name="Icon Wrapper"]').forEach(icon=>icon.remove());
		    let toggle=shell.querySelector('.creative-soil-faq-toggle');
		    if(!toggle){
		      toggle=document.createElement('button');
		      toggle.type='button';
		      toggle.className='creative-soil-faq-toggle';
		      shell.append(toggle);
		    }
		    applyState(card,false);
		    makeInteractive(toggle,()=>{
		      const next=card.dataset.creativeSoilFaqOpen!=='true';
		      cards.forEach(other=>{if(other!==card)applyState(other,false)});
		      applyState(card,next);
		    });
		  });
		};

	const initPricing=()=>{
	  let cards=document.querySelector('[data-framer-name="Plans Cards"]');
	  const cleanText=node=>(node&&node.textContent||'').replace(/\s+/g,'').toLowerCase();
	  const controlNodes=[...document.querySelectorAll('[data-framer-name="Free"],[data-framer-name="Premium"]')];
	  const starting=controlNodes.find(node=>cleanText(node)==='starting');
	  const growth=controlNodes.find(node=>cleanText(node)==='growth');
	  if(!cards||!growth||!starting)return;
	  const startingMarkup=cards.outerHTML;
	  const switcher=starting.parentElement&&starting.parentElement.querySelector('[data-framer-name="Main Switcher"]');
	  if(switcher)switcher.style.setProperty('display','none','important');
	  const paintControl=(node,active)=>{
	    const foreground=active?'#FFFFFF':'#1F363E';
	    node.classList.toggle('creative-soil-toggle-active',active);
	    node.setAttribute('aria-pressed',String(active));
	    node.style.setProperty('background-color',active?'#1F363E':'transparent','important');
	    node.style.setProperty('color',foreground,'important');
	    node.querySelectorAll('*').forEach(child=>child.style.setProperty('color',foreground,'important'));
	  };
	  const showState=active=>{
	    const activeGrowth=active==='growth';
	    paintControl(growth,activeGrowth);
	    paintControl(starting,!activeGrowth);
	  };
	  const clearInitialStates=root=>root.querySelectorAll('[style]').forEach(node=>{
	    const style=node.getAttribute('style')||'';
	    if(/opacity:\s*0(?:\.0*1)?(?:[;.\s]|$)/i.test(style))node.style.setProperty('opacity','1','important');
	    if(/filter:\s*blur\(/i.test(style))node.style.setProperty('filter','blur(0px)','important');
	    if(/translate(?:3d|X|Y)\(/i.test(style))node.style.setProperty('transform','none','important');
	  });
	  		  const normalizePlanContent=root=>{
		    root.querySelectorAll('a[href]').forEach(link=>{
		      const label=cleanText(link);
		      if(!label.includes('let’stalk')&&!label.includes("let'stalk"))return;
		      const container=link.closest('.framer-v67e3k-container')||link.parentElement;
		      if(container)container.classList.add('creative-soil-plan-cta');
		      /* Framer exports the CTA as individually animated letters. Replace that
		         presentation-only markup with one stable accessible text node. */
		      link.textContent='Let’s Talk!';
		      link.setAttribute('aria-label','Let’s Talk');
		      if(container){
		        container.style.setProperty('display','block','important');
		        container.style.setProperty('width','100%','important');
		        container.style.setProperty('min-width','0','important');
		      }
		      link.style.setProperty('display','flex','important');
		      link.style.setProperty('box-sizing','border-box','important');
		      link.style.setProperty('width','100%','important');
		      link.style.setProperty('min-width','0','important');
		      link.style.setProperty('max-width','none','important');
		      link.style.setProperty('min-height','52px','important');
		      link.style.setProperty('align-items','center','important');
		      link.style.setProperty('justify-content','center','important');
		      link.style.setProperty('border','1px solid #1F363E','important');
		      link.style.setProperty('border-radius','455px','important');
		      link.style.setProperty('background','#F5D636','important');
		      link.style.setProperty('color','#1F363E','important');
		      link.style.setProperty('font','700 18px/1 Satoshi,Arial,sans-serif','important');
		      link.style.setProperty('padding','14px 28px','important');
		      link.style.setProperty('white-space','nowrap','important');
		      link.style.setProperty('word-break','normal','important');
		      link.style.setProperty('overflow-wrap','normal','important');
		      link.style.setProperty('writing-mode','horizontal-tb','important');
		      link.style.setProperty('text-orientation','mixed','important');
		      link.style.setProperty('text-align','center','important');
		      link.style.setProperty('line-height','1','important');
		    });
		  };

	  const swap=markup=>{
	    const temporary=document.createElement('div');
	    temporary.innerHTML=markup.trim();
	    const next=temporary.firstElementChild;
	    if(!next)return;
	    cards.replaceWith(next);
	    cards=next;
	    clearInitialStates(cards);
	    normalizePlanContent(cards);
	    repairLinks(cards);
	  };
	  const chooseStarting=()=>{swap(startingMarkup);showState('starting')};
	  const chooseGrowth=async()=>{
	    if(growth.dataset.creativeSoilLoading==='true')return;
	    growth.dataset.creativeSoilLoading='true';
	    try{
	      const response=await fetch('/static-data/growth-plan.json',{cache:'no-store'});
	      if(!response.ok)throw new Error('Growth plan unavailable');
	      const data=await response.json();
	      swap(data.html||'');
	      showState('growth');
	    }catch(error){
	      console.error('Creative Soil Growth plan could not be loaded',error);
	    }finally{delete growth.dataset.creativeSoilLoading}
	  };
	  normalizePlanContent(cards);
	  showState('starting');
	  makeInteractive(starting,chooseStarting);
	  makeInteractive(growth,chooseGrowth);
	};

	const initIdeasSearch=()=>{
	  const host=document.querySelector('[data-framer-name="Search Input"]')||document.querySelector('.framer-13rsm5n');
	  if(!host||host.dataset.creativeSoilSearchReady==='true')return;
	  host.dataset.creativeSoilSearchReady='true';
	  /* Hide Framer's visual placeholder and icon layers, which otherwise overlap
	     the working input in a static export. */
	  [...host.children].forEach(node=>{
	    node.setAttribute('aria-hidden','true');
	    node.style.setProperty('display','none','important');
	  });
	  const icon=document.createElement('span');
	  icon.className='creative-soil-search-icon';
	  icon.setAttribute('aria-hidden','true');
	  icon.textContent='⌕';
	  const input=document.createElement('input');
	  input.type='search';
	  input.autocomplete='off';
	  input.placeholder='Search articles…';
	  input.className='creative-soil-ideas-search';
	  input.setAttribute('aria-label','Search articles');
	  host.append(icon,input);
	  const cards=[...document.querySelectorAll('a[data-framer-name="Primary"],a[data-framer-name="Featured"]')].filter(card=>/ideas\//.test(card.getAttribute('href')||''));
	  input.addEventListener('input',()=>{
	    const query=input.value.trim().toLowerCase();
	    cards.forEach(card=>{
	      const matches=!query||(card.textContent||'').toLowerCase().includes(query);
	      card.style.setProperty('display',matches?'':'none','important');
	      card.setAttribute('aria-hidden',String(!matches));
	    });
	  });
	};

	const initArticleCta=()=>{
	  if(!/^\/ideas\//.test(location.pathname))return;
	  const section=document.querySelector('section[data-framer-name="CTA Section"]');
	  if(!section||section.dataset.creativeSoilArticleCtaReady==='true')return;
	  section.dataset.creativeSoilArticleCtaReady='true';
	  const compact=node=>(node.textContent||'').replace(/\s+/g,'').toLowerCase();
	  const links=[...section.querySelectorAll('a[href]')].filter(link=>compact(link).includes('let’screatetogether')||compact(link).includes("let'screatetogether"));
	  links.forEach(link=>{
	    link.classList.add('creative-soil-article-cta-link');
	    link.setAttribute('href','/contact/');
	    if(link.dataset.creativeSoilCtaTextReady!=='true'){
	      link.textContent='LET’S CREATE TOGETHER';
	      const arrow=document.createElement('span');
	      arrow.className='creative-soil-article-cta-arrow';
	      arrow.setAttribute('aria-hidden','true');
	      arrow.textContent='↗';
	      link.append(arrow);
	      link.dataset.creativeSoilCtaTextReady='true';
	    }
	  });
	  const media=document.createElement('div');
	  media.className='creative-soil-article-cta-media';
	  media.setAttribute('aria-hidden','true');
	  [
	    '/images/TvbNAslFrkkBynAWAqBoTTzCGk_109f5d82.jpg',
	    '/images/D8DGgVarijjA3tDvJ3P1cy5E_37905bd4.jpg',
	    '/images/mQdFF81yk2k4uo1LQKgAGQPsAvc_d2af55ac.png'
	  ].forEach(src=>{
	    const image=document.createElement('img');
	    image.src=src;image.alt='';image.loading='lazy';
	    media.append(image);
	  });
	  section.append(media);
	};
	const initContactForm=()=>{

  const form=document.querySelector('form.framer-vsw57k')||document.querySelector('form');
  if(!form||form.dataset.creativeSoilContactReady==='true'||form.dataset.creativeSoilNativeForm==='true')return;
  const endpoint='https://script.google.com/macros/s/AKfycbyQmst6wuOIOW71hE6UmzkqQ6czMp0oslI8XcrSn4Kf45dfCSmo-enx2u_xskmZH4FDlA/exec';
  const frameName='creative-soil-contact-receiver';
  let frame=document.querySelector(`iframe[name="${frameName}"]`);
  if(!frame){
    frame=document.createElement('iframe');
    frame.name=frameName;
    frame.title='Contact form submission receiver';
    frame.setAttribute('aria-hidden','true');
    frame.tabIndex=-1;
    frame.style.cssText='display:none!important;width:0!important;height:0!important;border:0!important';
    document.body.append(frame);
  }
  const status=document.createElement('p');
  status.className='creative-soil-contact-status';
  status.setAttribute('role','status');
  status.setAttribute('aria-live','polite');
  status.style.cssText='display:none;margin:14px 0 0;color:#FFFFFF;font:inherit;line-height:1.4';
  form.append(status);
  form.action=endpoint;
  form.method='post';
  form.target=frameName;
  form.acceptCharset='UTF-8';
  form.dataset.creativeSoilContactReady='true';
  const button=form.querySelector('[type="submit"]');
  const setStatus=(message,visible=true)=>{
    status.textContent=message;
    status.style.display=visible?'block':'none';
  };
  let awaitingResponse=false;
  const complete=()=>{
    if(!awaitingResponse)return;
    awaitingResponse=false;
    form.reset();
    if(button){button.removeAttribute('aria-disabled');button.style.removeProperty('pointer-events');button.style.removeProperty('opacity');}
    setStatus('Thank you — your message has been received. We will be in touch soon.');
  };
  frame.addEventListener('load',()=>{if(awaitingResponse)complete();});
  form.addEventListener('submit',event=>{
    if(!form.checkValidity())return;
    if(awaitingResponse){event.preventDefault();return;}
    awaitingResponse=true;
    if(button){button.setAttribute('aria-disabled','true');button.style.setProperty('pointer-events','none');button.style.setProperty('opacity','.72');}
    setStatus('Sending your message…');
    window.setTimeout(complete,5000);
  });
};
	const initFooterContact=()=>{
	  if(location.pathname.replace(/\/+$/,'')==='/contact')return;
	  document.querySelectorAll('[data-framer-name="Email & Phone Number"]').forEach(block=>{
	    if(block.dataset.creativeSoilFooterEmailReady==='true')return;
	    const phone=block.querySelector('a[href^="tel:"]');
	    if(!phone)return;
	    const phoneContainer=phone.closest('[data-framer-component-type="RichTextContainer"]');
	    if(!phoneContainer)return;
	    let emailContainer=[...block.children].find(child=>child!==phoneContainer&&!child.querySelector('a[href]'));
	    if(!emailContainer){
	      emailContainer=phoneContainer.cloneNode(true);
	      phoneContainer.after(emailContainer);
	    }
	    const paragraph=emailContainer.querySelector('p')||emailContainer;
	    paragraph.textContent='';
	    const email=phone.cloneNode(true);
	    email.href='mailto:liza@creativesoil.co';
	    email.textContent='liza@creativesoil.co';
	    email.removeAttribute('target');
	    email.removeAttribute('rel');
	    email.setAttribute('data-creative-soil-footer-email','true');
	    paragraph.append(email);
	    block.append(emailContainer);
	    block.dataset.creativeSoilFooterEmailReady='true';
	  });
	};
		const initContactChrome=()=>{
  if(location.pathname.replace(/\/+$/,'')!=='/contact')return;
  const compact=node=>(node.textContent||'').replace(/\s+/g,'').toLowerCase();
  document.querySelectorAll('a').forEach(anchor=>{
    if(compact(anchor).includes('conditions')){
      const block=anchor.closest('p')||anchor;
      if(block&&block.isConnected)block.remove();
    }
    if(compact(anchor)==='hello@creativesoil.co'||compact(anchor)==='liza@creativesoil.co'){
      anchor.textContent='liza@creativesoil.co';
      anchor.setAttribute('href','mailto:liza@creativesoil.co');
    }
  });
  document.querySelectorAll('[data-framer-name="Email & Phone Number"]').forEach(block=>{
    const phone=block.querySelector('a[href^="tel:"]');
    const email=[...block.querySelectorAll('a[href^="mailto:"]')].find(anchor=>compact(anchor)==='liza@creativesoil.co');
    const phoneContainer=phone?.closest('[data-framer-component-type="RichTextContainer"]');
    const emailContainer=email?.closest('[data-framer-component-type="RichTextContainer"]');
    if(phoneContainer&&emailContainer&&phoneContainer!==emailContainer)phoneContainer.after(emailContainer);
  });
  const positionWorksLink=()=>{
    const links=document.querySelector('nav[data-framer-name="Desktop"] [data-framer-name="Links"]');
    const ideas=[...links?.querySelectorAll('a[href]')||[]].find(anchor=>compact(anchor)==='ideas');
    if(!links||!ideas)return;
    let works=document.getElementById('creative-soil-contact-works-link');
    if(!works){
      works=document.createElement('a');
      works.id='creative-soil-contact-works-link';
      works.href='/works/';
      works.setAttribute('aria-label','Works');
      works.innerHTML='<span class="creative-soil-works-label">Works</span>';
      document.body.append(works);
    }
    const rect=ideas.getBoundingClientRect();
    const gap=8;
    const width=Math.max(ideas.offsetWidth,64);
    works.style.setProperty('width',width+'px','important');
    works.style.setProperty('left',(rect.left-width-gap)+'px','important');
    works.style.setProperty('top',(rect.top+(rect.height-40)/2)+'px','important');
  };
  positionWorksLink();
  if(!window.__creativeSoilWorksPositionReady){
    window.__creativeSoilWorksPositionReady=true;
    window.addEventListener('resize',positionWorksLink,{passive:true});
    window.addEventListener('scroll',positionWorksLink,{passive:true});
  }
  if(!window.__creativeSoilContactChromeObserver){
    let scheduled=false;
    const schedule=()=>{
      if(scheduled)return;
      scheduled=true;
      window.setTimeout(()=>{scheduled=false;initContactChrome();},40);
    };
    const observer=new MutationObserver(schedule);
    observer.observe(document.body,{childList:true,subtree:true});
    window.__creativeSoilContactChromeObserver=observer;
    window.setTimeout(()=>{observer.disconnect();delete window.__creativeSoilContactChromeObserver;},15000);
  }
};

		const start=()=>{

		  installInteractionStyles();repairLinks();initFaq();initPricing();initIdeasSearch();initArticleCta();initContactForm();initFooterContact();initContactChrome();

  [80,240,700,1600,3200,6000,10000,14000].forEach(delay=>window.setTimeout(initContactChrome,delay));
};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();"""

CONTACT_CHROME_RUNTIME = r"""(()=>{
  const compact=node=>(node.textContent||'').replace(/\s+/g,'').toLowerCase();
  const applyNavigation = () => {
  document.querySelectorAll('[data-framer-name="Links"]').forEach((links) => {
    const anchors = [...links.querySelectorAll(':scope > a[href]')];
    const ideas = anchors.find((a) => (a.textContent || '').replace(/\s+/g, '').toLowerCase().startsWith('ideas'));
    if (!ideas || anchors.some((a) => (a.textContent || '').replace(/\s+/g, '').toLowerCase().startsWith('works'))) return;

    const works = ideas.cloneNode(true);
    works.href = '/works/';
    works.style.setProperty('pointer-events', 'auto', 'important');
    works.style.setProperty('cursor', 'pointer', 'important');
    works.style.setProperty('color', '#000', 'important');

    const rolling = works.querySelector('p[class*="rolling-text-inner"]');
    if (rolling) {
      rolling.style.setProperty('color', '#000', 'important');
      const letters = [...rolling.querySelectorAll('span')];
      ['W', 'o', 'r', 'k', 's'].forEach((letter, index) => {
        if (letters[index]) letters[index].textContent = letter;
      });
    }

    works.addEventListener('click', (event) => {
      event.preventDefault();
      window.location.assign('/works/');
    });

    ideas.before(works);
  });
};
  const applyFooter=()=>{
    document.querySelectorAll('[data-framer-name="Email & Phone Number"]').forEach(block=>{
      const phone=block.querySelector('a[href^="tel:"]');
      let email=[...block.querySelectorAll('a[href^="mailto:"]')].find(anchor=>/creativesoil\.co$/i.test(compact(anchor)));
      if(!email){
        const source=phone?.closest('[data-framer-component-type="RichTextContainer"]');
        if(!source)return;
        const copy=source.cloneNode(true);
        const paragraph=copy.querySelector('p')||copy;
        paragraph.textContent='';
        email=document.createElement('a');
        paragraph.append(email);
        block.append(copy);
      }
      email.href='mailto:liza@creativesoil.co';
      email.textContent='liza@creativesoil.co';
      const phoneContainer=phone?.closest('[data-framer-component-type="RichTextContainer"]');
      const emailContainer=email.closest('[data-framer-component-type="RichTextContainer"]');
      if(phoneContainer&&emailContainer&&phoneContainer!==emailContainer)phoneContainer.after(emailContainer);
    });
  };
  const apply=()=>{applyNavigation();applyFooter();};
  const start=()=>[300,900,1800,3200,6000,10000].forEach(delay=>setTimeout(apply,delay));
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();"""


def repair_internal_href(value: str, current_route: str = "/") -> str:
    """Correct export truncations and make relative internal routes stable."""
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith("#"):
        return value
    raw_path = parsed.path
    if current_route.startswith("/ideas/") and raw_path.startswith("./"):
        # Framer used ./article-slug for sibling cards; static hosting resolves that
        # inside the current article directory, so explicitly target /ideas/ instead.
        raw_path = "/ideas/" + raw_path[2:]
    elif raw_path and not raw_path.startswith("/"):
        base = "https://test3.local" + current_route.rstrip("/") + "/"
        raw_path = urlparse(urljoin(base, raw_path)).path
    path = re.sub(r"(/ideas/[^/]+)\\.(?=/?$)", r"\\1", raw_path)
    if path.startswith("/ideas/"):
        path = path.replace(".", "")
    replacements = {
        "/contac": "/contact",
        "/works/fa": "/works/fatt",
        "/works/roa": "/works/roam",
        "/works/recla": "/works/reclaim",
        "/ideas/the-harrods-halo-effect-the-secret-listing-that-will-transform-your-entire-food-bra": "/ideas/the-harrods-halo-effect-the-secret-listing-that-will-transform-your-entire-food-brand",
        "/ideas/are-you-burning-cash-on-digital-ads-while-your-competitors-scale-for-fr": "/ideas/are-you-burning-cash-on-digital-ads-while-your-competitors-scale-for-free",
        "/ideas/the-brutal-reason-your-wellness-drink-is-dying-on-the-shelf.": "/ideas/the-brutal-reason-your-wellness-drink-is-dying-on-the-shelf",
    }
    for wrong, correct in replacements.items():
        if path == wrong or path == wrong + "/":
            suffix = "/" if path.endswith("/") and not correct.endswith("/") else ""
            path = correct + suffix
            break
        if path.endswith(wrong) or path.endswith(wrong + "/"):
            path = path.replace(wrong, correct)
            break
    result = path
    if parsed.query:
        result += "?" + parsed.query
    if parsed.fragment:
        result += "#" + parsed.fragment
    return result


def local_font_file_by_source_name(source_filename: str) -> str | None:
    """Return the local hashed copy for a Framer source font filename, if present."""
    for candidate in ROOT.joinpath("fonts").glob("*.woff2"):
        if candidate.stem.rsplit("_", 1)[0] == source_filename.rsplit(".woff2", 1)[0]:
            return candidate.name
    return None


def rebase_external_woff2(match: re.Match[str]) -> str:
    local_name = local_font_file_by_source_name(match.group("filename"))
    return f"/fonts/{local_name}" if local_name else match.group(0)


def route_from_path(path: Path) -> str:
    relative = path.relative_to(ROOT)
    if relative == Path("index.html"):
        return "/"
    if relative.name == "index.html":
        return "/" + relative.parent.as_posix()
    return "/" + relative.with_suffix("").as_posix()


def remove_template_anchor(anchor) -> bool:
    wrapper = anchor.find_parent(
        "div",
        class_=lambda value: value
        and any(
            item.endswith("-container")
            for item in (value if isinstance(value, list) else str(value).split())
        ),
    )
    (wrapper or anchor).decompose()
    return True


def local_href(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path or "/"
    result = path
    if parsed.query:
        result += "?" + parsed.query
    if parsed.fragment:
        result += "#" + parsed.fragment
    return result


def inject_protection(soup: BeautifulSoup, route: str) -> None:
    if soup.head is None:
        return
    for existing in list(soup.select('[data-creative-soil-static-repair="true"]')):
        existing.decompose()
    style = soup.new_tag("style")
    style["data-creative-soil-static-repair"] = "true"
    style.string = STATIC_PROTECTION_CSS + ("\n" + LEGAL_BULLET_CSS if route in {"/privacy-policy", "/terms-conditions"} else "")
    soup.head.append(style)
    sanitizer = soup.new_tag("script")
    sanitizer["data-creative-soil-static-repair"] = "true"
    sanitizer.string = RUNTIME_SANITIZER
    soup.head.append(sanitizer)
    animator = soup.new_tag("script")
    animator["data-creative-soil-static-repair"] = "true"
    animator.string = STATIC_APPEAR_ANIMATOR
    soup.head.append(animator)
    text_reveal = soup.new_tag("script")
    text_reveal["data-creative-soil-static-repair"] = "true"
    text_reveal.string = STATIC_TEXT_REVEAL_ANIMATOR
    soup.head.append(text_reveal)
    interactions = soup.new_tag("script")
    interactions["data-creative-soil-static-repair"] = "true"
    interactions.string = STATIC_INTERACTION_RUNTIME
    soup.head.append(interactions)


def transform(path: Path) -> tuple[str, dict[str, int | str]]:
    original = path.read_text(encoding="utf-8")
    route = route_from_path(path)
    if route == "/contact":
        # Preserve the exact Framer SSR markup so React can hydrate its working form.
        # The header/footer adjustments are injected after hydration rather than mutating it.
        runtime_tag = '<script data-creative-soil-contact-chrome="true">' + CONTACT_CHROME_RUNTIME + '</script>'
        rendered = original.replace('</body>', runtime_tag + '</body>')
        if not rendered.lstrip().lower().startswith('<!doctype'):
            rendered = '<!DOCTYPE html>\n' + rendered
        return rendered, {
            'route': route,
            'badge_nodes_removed': 0,
            'editor_nodes_removed': 0,
            'editor_assets_removed': 0,
            'framer_runtime_assets_removed': 0,
            'template_ctas_removed': 0,
            'generator_meta_removed': 0,
            'framer_comments_removed': 0,
            'font_paths_rebased': 0,
            'external_font_paths_localized': 0,
            'image_style_paths_rebased': 0,
            'image_attribute_paths_rebased': 0,
        }
    soup = BeautifulSoup(original, "html.parser")
    stats: dict[str, int | str] = {
        "route": route,
        "badge_nodes_removed": 0,
        "editor_nodes_removed": 0,
        "editor_assets_removed": 0,
        "framer_runtime_assets_removed": 0,
        "template_ctas_removed": 0,
        "generator_meta_removed": 0,
        "framer_comments_removed": 0,
    }

    for comment in list(soup.find_all(string=lambda value: isinstance(value, Comment))):
        comment_text = str(comment)
        if "Made in Framer" in comment_text or "Published " in comment_text:
            comment.extract()
            stats["framer_comments_removed"] += 1

    for meta in list(soup.find_all("meta")):
        name = (meta.get("name") or "").lower()
        if name == "generator" or name.startswith("framer-search-index"):
            meta.decompose()
            stats["generator_meta_removed"] += 1

    for asset in list(soup.find_all(["script", "link"])):
        src = asset.get("src", "")
        href = asset.get("href", "")
        text = asset.get_text(" ", strip=False)
        asset_url = (src or href).lower()
        rel = asset.get("rel", [])
        rel_values = rel if isinstance(rel, list) else str(rel).split()
        is_editor_asset = (
            "framer.com/edit/init.mjs" in asset_url
            or "editorbar" in asset_url
            or "__framer_force_showing_editorbar_since" in text
        )
        is_static_runtime_asset = (
            (asset.name == "script" and (
                "events.framer.com/script" in asset_url
                or asset.get("data-framer-bundle") == "main"
                or asset.has_attr("data-framer-appear-animation")
                or asset.get("type") == "framer/appear"
                or asset.get("id") in {"__framer__appearAnimationsContent", "__framer__breakpoints"}
            ))
            or (asset.name == "link" and "framerusercontent.com/sites/" in asset_url and "modulepreload" in rel_values)
        )
        if is_editor_asset:
            asset.decompose()
            stats["editor_assets_removed"] += 1
        elif is_static_runtime_asset:
            preserve_contact_form_runtime = route == "/contact" and (
                (asset.name == "script" and asset.get("data-framer-bundle") == "main")
                or (
                    asset.name == "link"
                    and "framerusercontent.com/sites/" in asset_url
                    and "modulepreload" in rel_values
                )
            )
            if not preserve_contact_form_runtime:
                asset.decompose()
                stats["framer_runtime_assets_removed"] += 1

    for selector, key in (
        ("#__framer-badge-container, .__framer-badge", "badge_nodes_removed"),
        (
            "#__framer-editorbar-container, #__framer-editorbar, #__framer-editorbar-button, #__framer-editorbar-label",
            "editor_nodes_removed",
        ),
    ):
        for node in list(soup.select(selector)):
            if node.parent is not None:
                node.decompose()
                stats[key] += 1

    for anchor in list(soup.find_all("a", href=True)):
        href = str(anchor.get("href", ""))
        if href.startswith("https://framer.link/") or href.rstrip("/") == "https://www.framer.com":
            if remove_template_anchor(anchor):
                stats["template_ctas_removed"] += 1
            continue
        if href.startswith(SOURCE_ORIGIN):
            anchor["href"] = repair_internal_href(local_href(href), route)
        elif href in HOMEPAGE_HERO_LINKS:
            anchor["href"] = "/"
        else:
            anchor["href"] = repair_internal_href(href, route)
        text = anchor.get_text(" ", strip=True)
        if text == "hello@creativesoil.co":
            anchor["href"] = "mailto:hello@creativesoil.co"
        elif text == "+44 7542 866885":
            anchor["href"] = "tel:+447542866885"

    if soup.head is not None:
        canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
        canonical_url = TEST_ORIGIN + route
        if canonical:
            canonical["href"] = canonical_url
        else:
            soup.head.append(soup.new_tag("link", rel="canonical", href=canonical_url))
        og_url = soup.find("meta", attrs={"property": "og:url"})
        if og_url:
            og_url["content"] = canonical_url
        else:
            new_og_url = soup.new_tag("meta")
            new_og_url["property"] = "og:url"
            new_og_url["content"] = canonical_url
            soup.head.append(new_og_url)

    inject_protection(soup, route)
    rendered = str(soup)

    rendered, font_paths = FONT_URL_RE.subn(
        lambda match: f"url({match.group('quote')}/fonts/{match.group('path')}{match.group('quote')})",
        rendered,
    )
    rendered, image_style_paths = IMAGE_URL_RE.subn(
        lambda match: f"url({match.group('quote')}/images/{match.group('path')}{match.group('quote')})",
        rendered,
    )
    rendered, image_attr_paths = RELATIVE_IMAGE_ATTR_RE.subn(
        lambda match: f"{match.group('prefix')}/images/",
        rendered,
    )
    rendered, external_font_paths = EXTERNAL_WOFF2_RE.subn(rebase_external_woff2, rendered)

    for broken, correct in ENCODING_REPAIRS.items():
        rendered = rendered.replace(broken, correct)
    for old_colour, new_colour in BRAND_COLOUR_REPAIRS.items():
        rendered = rendered.replace(old_colour, new_colour)
    rendered = rendered.replace("2025", "2026")
    rendered = rendered.replace(SOURCE_ORIGIN, TEST_ORIGIN)
    rendered = rendered.replace("creativesoil.framer.website", "test3-liza-2565s-projects.vercel.app")
    rendered = rendered.replace("https:\\/\\/creativesoil.framer.website", "https:\\/\\/test3-liza-2565s-projects.vercel.app")
    if not rendered.lstrip().lower().startswith("<!doctype"):
        rendered = "<!DOCTYPE html>\n" + rendered

    stats["font_paths_rebased"] = font_paths
    stats["external_font_paths_localized"] = external_font_paths
    stats["image_style_paths_rebased"] = image_style_paths
    stats["image_attribute_paths_rebased"] = image_attr_paths
    return rendered, stats


def _compact_text(node) -> str:
    return "".join(node.get_text(" ", strip=True).split()).lower()


def restore_reference_pages() -> None:
    """Restore known-good exported source pages before static transformations.

    The source article's original Framer slug ends with a terminal period, while
    the test3 route deliberately omits that period. The contact page retains its
    proven Framer form runtime, with only the user-requested navigation changes.
    """
    article_source = REFERENCE_ROOT / "ideas" / "the-brutal-reason-your-wellness-drink-is-dying-on-the-shelf..html"
    article_target = ROOT / "ideas" / "the-brutal-reason-your-wellness-drink-is-dying-on-the-shelf" / "index.html"
    contact_source = REFERENCE_ROOT / "contact.html"
    contact_target = ROOT / "contact" / "index.html"

    if not article_source.exists() or not contact_source.exists():
        raise RuntimeError("Known-good Creative Soil reference pages are unavailable")

    article_target.parent.mkdir(parents=True, exist_ok=True)
    article_target.write_text(article_source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

    # Copy the working Framer contact page byte-for-byte. It must remain unchanged
    # before its native React runtime hydrates the form.
    contact_target.parent.mkdir(parents=True, exist_ok=True)
    contact_target.write_text(contact_source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


def main() -> None:
    restore_reference_pages()
    html_files = sorted(ROOT.rglob("*.html"))
    if not html_files:
        raise RuntimeError(f"No HTML files found in {ROOT}")

    report = []
    for path in html_files:
        rendered, stats = transform(path)
        path.write_text(rendered, encoding="utf-8", newline="\n")
        report.append({"file": path.relative_to(ROOT).as_posix(), **stats})

    summary = {
        "root": str(ROOT),
        "files_repaired": len(report),
        "totals": {
            key: sum(int(item.get(key, 0)) for item in report)
            for key in (
                "badge_nodes_removed",
                "editor_nodes_removed",
                "editor_assets_removed",
                "framer_runtime_assets_removed",
                "template_ctas_removed",
                "generator_meta_removed",
                "framer_comments_removed",
                "font_paths_rebased",
                "external_font_paths_localized",
                "image_style_paths_rebased",
                "image_attribute_paths_rebased",
            )
        },
        "files": report,
    }
    REPORT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
