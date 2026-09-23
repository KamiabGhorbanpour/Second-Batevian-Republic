import base64
import json
import re
import zlib
from pathlib import Path

path = Path("main.py")
wrapper = path.read_text(encoding="utf-8")

def unpack(name: str) -> str:
    m = re.search(rf"(?m)^{name} = '([^']+)'$", wrapper)
    if not m:
        raise RuntimeError(f"Could not find {name}")
    return zlib.decompress(base64.b64decode(m.group(1))).decode("utf-8")

app = unpack("_MAIN")
story = json.loads(unpack("_STORY"))
css = unpack("_CSS")

literature_overviews = {
    (1, "education", 0): "Unrestricted AI improved assisted work but harmed later unaided performance. Meta-analytic work also finds that AI can support learning in some settings, so the literature supports the ending as a risk of unrestricted answer-giving rather than a claim that all AI tutoring harms learning.",
    (1, "education", 1): "Studies of guardrailed tutoring and process-focused assessment suggest that supervised use can preserve more of the learning benefit while reducing over-reliance. This supports the ending in which AI remains useful, but teachers carry more of the monitoring and guidance burden.",
    (1, "education", 2): "Research comparing AI-prohibited and AI-permissive assessment shows that restricting AI can better preserve independent performance, while enforcement remains difficult. That supports steadier unaided learning alongside a continuing struggle with hidden use.",
    (1, "foreign", 0): "Research on meaningful human control and military-AI governance argues that autonomous systems need clear responsibility and shared rules. This supports diplomatic gains from pursuing safeguards while also reflecting continued disagreement over what military uses should actually be restricted.",
    (1, "foreign", 1): "Work on meaningful human control, explainability and the 'algorithmic fog of war' shows that keeping a human in the loop does not automatically guarantee independent judgement, especially under time pressure. This supports faster targeting alongside operators becoming dependent on AI recommendations.",
    (1, "foreign", 2): "Research on accountability and transparency in military AI warns that rapid, opaque human-machine decision chains can blur responsibility when failures occur. This supports the ending in which targeting accelerates but officials struggle to determine whether a mistaken strike came from data, the model or the human decision around it.",
    (1, "interior", 0): "Predictive-policing research documents feedback loops in which models trained on recorded police activity repeatedly direct officers back to already heavily policed areas. This supports intensified policing of poorer neighbourhoods and the difficulty of separating model error from existing institutional patterns.",
    (1, "interior", 1): "Research on facial recognition, predictive policing and public-sector AI oversight stresses warrants, justification, auditability and appeal. This supports narrower deployment with stronger safeguards, while also implying extra technical and administrative costs.",
    (1, "interior", 2): "Research shows that predictive policing can create self-reinforcing feedback loops, while field experiments also find that predictive tools can sometimes help allocate police resources. This supports the trade-off in the ending: prohibition avoids those feedback risks but gives up possible efficiency gains.",
    (1, "social", 0): "Experimental and workplace studies find substantial productivity gains from generative AI, while labour-market evidence suggests jobs may be reorganised rather than disappearing uniformly. This supports rapid productivity growth together with fewer routine junior tasks and changing skill demands.",
    (1, "social", 1): "Meta-analyses of labour-market programmes find that retraining can modestly improve re-employment and wages, especially when training is practical and linked to employers. This supports cushioning displacement without implying that retraining can eliminate all of the costs of automation.",
    (1, "social", 2): "Productivity research shows that AI assistance can generate meaningful efficiency gains. That supports the opportunity cost in the ending: protecting specified human roles may preserve jobs, but firms still have incentives to automate surrounding tasks and absorb higher labour costs.",
    (2, "education", 0): "Studies find that LLMs can fabricate or corrupt bibliographic references, which makes provenance and disclosure useful for tracing errors. Other work finds that disclosure alone does not necessarily restore trust, supporting an ending where traceability improves without solving hidden use.",
    (2, "education", 1): "Research documents persistent fabricated and unverifiable AI-generated citations, making verification skills and checking systems directly relevant. This supports the ending in which bogus references are caught earlier and users become less vulnerable to material that only looks scholarly.",
    (2, "education", 2): "Studies of journal AI rules suggest that formal prohibitions and disclosure requirements do not reliably eliminate AI-assisted writing, while visible AI use can reduce perceived trust. This supports an ending where the official record looks cleaner but some use moves off the record.",
    (2, "foreign", 0): "Meta-analytic research on misinformation correction finds that debunking can reduce false beliefs but often leaves a continued-influence effect. This supports a rapid-response team containing some claims without fully stopping their spread, especially among audiences that already distrust official sources.",
    (2, "foreign", 1): "Studies of media literacy, inoculation and prebunking find modest but real improvements in people's ability to distinguish reliable from false content. This supports slow and uneven gains in public scepticism rather than an immediate solution to synthetic propaganda.",
    (2, "foreign", 2): "Research on synthetic-media labels and fact-checking suggests that labels can help users identify manipulated content, but effects depend heavily on implementation and context. This supports making obvious campaigns harder to spread while leaving disputes over inconsistent enforcement.",
    (2, "interior", 0): "Studies of AI-media labels show that warnings can help but are not sufficient, while deepfake-literacy research finds that people remain poor at detecting convincing synthetic media. This supports easier identification of some fakes without eliminating fraud or deception.",
    (2, "interior", 1): "Research on voice-clone detection shows that people are often unable to identify convincing synthetic voices reliably. This supports safeguards at the tool level reducing casual impersonation, while determined attackers can still move to less regulated services.",
    (2, "interior", 2): "Digital-identity standards and deepfake attack research support stronger, independent identity checks for high-risk services because face or voice evidence can be spoofed. This supports lower fraud risk in the ending, while the extra verification steps also make services slower and less convenient.",
    (2, "social", 0): "Research on verifiable educational credentials finds that they can reduce fraud and verification burden, although interoperability remains difficult. This supports harder-to-fake qualifications together with a new dependence on credential infrastructure.",
    (2, "social", 1): "Identity-proofing standards and deepfake attack research support stronger checks for high-risk transactions because face-based verification can be attacked. This supports catching more fraudulent applicants while also adding friction to remote hiring.",
    (2, "social", 2): "Research finds that employer understanding and adoption of digital credentials are uneven, while credential systems face interoperability and governance barriers. This supports a market where stronger firms build better checks and fraud concentrates where verification is weakest.",
    (3, "education", 0): "Creativity studies find that AI can raise individual output quality while making outputs more similar to one another. This supports higher production capacity for smaller studios together with a narrower collective style, although the effect of public funding itself is not directly tested.",
    (3, "education", 1): "Copyright and remuneration research suggests that compensating creators can preserve incentives while increasing transaction and training costs for AI firms. This supports an ending where creators receive income but model development and data access become slower or more expensive.",
    (3, "education", 2): "Studies of AI-assisted creativity find that individual works can improve while collective diversity falls, and human-only work can contribute more novel ideas. This supports abundant, polished synthetic culture alongside greater homogeneity and weaker creator bargaining power.",
    (3, "foreign", 0): "Research on public-sector procurement and cloud lock-in shows that proprietary standards, data dependencies and opaque contracts can make switching suppliers costly. This supports an ending where capability arrives quickly but long-term strategic dependence deepens.",
    (3, "foreign", 1): "Research on technological sovereignty argues that retaining auditable infrastructure and domestic capability can reduce vendor dependence and preserve policy room. This supports greater long-term autonomy, while the short-term capability gap remains a scenario trade-off.",
    (3, "foreign", 2): "Research on cloud dependency and interoperability shows that open interfaces and portability can reduce lock-in without eliminating it. This supports buying time and learning from a supplier while still failing to remove every point of dependence.",
    (3, "interior", 0): "Research on algorithmic administration warns that opaque systems can create a legitimacy gap when decisions are difficult to inspect or contest. This supports faster administration together with an accountability crisis when officials cannot explain a serious failure.",
    (3, "interior", 1): "Public-sector procurement and accountability research stresses interoperability, audit access and meaningful oversight. This supports easier switching and clearer responsibility, while some vendors may find those requirements unattractive or costly.",
    (3, "interior", 2): "Research on technological sovereignty and modular public infrastructure supports reducing dependence by retaining control over code, data and infrastructure. This fits an ending where sovereignty improves, while higher transition costs and rough early performance remain plausible implementation costs.",
    (3, "social", 0): "Economic research suggests that AI can increase wealth inequality through returns to capital even when wage effects are more mixed. This supports an ending where income support prevents destitution while a growing share of national income flows through capital and transfers rather than wages.",
    (3, "social", 1): "Meta-analyses find that retraining and employment services can modestly improve job-finding and wages, especially when tied to practical skills and real vacancies. This supports fewer workers leaving the labour market entirely, while outcomes remain uneven.",
    (3, "social", 2): "Distributional research shows that AI-related capital ownership can widen wealth gaps, while tax-and-transfer models show that policy can redistribute part of automation gains with efficiency trade-offs. This supports shifting some of the AI dividend toward workers and public revenue.",
}

extra_dois = {
    (1, "foreign", 0): ["https://doi.org/10.3389/frobt.2018.00015", "https://doi.org/10.1007/s10676-023-09683-0", "https://doi.org/10.1038/s42256-026-01231-x"],
    (1, "foreign", 1): ["https://doi.org/10.3389/frobt.2018.00015", "https://doi.org/10.1007/s10676-024-09762-w", "https://doi.org/10.3233/FRL-200019"],
    (1, "foreign", 2): ["https://doi.org/10.3233/FRL-200019", "https://doi.org/10.1038/s42256-026-01231-x"],
    (1, "interior", 0): ["https://doi.org/10.1080/10439463.2016.1253695"],
    (1, "interior", 1): ["https://doi.org/10.1177/20322844231212834"],
    (1, "interior", 2): ["https://doi.org/10.1007/s11292-019-09400-2"],
    (1, "social", 0): ["https://doi.org/10.1126/science.adh2586", "https://doi.org/10.1093/qje/qjae044"],
    (2, "foreign", 0): ["https://doi.org/10.1177/0093650219854600", "https://doi.org/10.1027/1016-9040/a000492"],
    (2, "foreign", 1): ["https://doi.org/10.1073/pnas.1920498117", "https://doi.org/10.1027/1016-9040/a000492"],
    (2, "foreign", 2): ["https://doi.org/10.1093/pnasnexus/pgaf170", "https://doi.org/10.1027/1016-9040/a000492"],
    (2, "interior", 0): ["https://doi.org/10.1093/pnasnexus/pgaf170", "https://doi.org/10.1038/s41598-025-94170-3"],
    (2, "interior", 1): ["https://doi.org/10.1038/s41598-025-94170-3"],
    (2, "interior", 2): ["https://doi.org/10.6028/NIST.SP.800-63A-4", "https://doi.org/10.1145/3485447.3512212"],
}

for stage_index, round_data in enumerate(story["rounds"], start=1):
    for ministry, decisions in round_data["decisions"].items():
        main_decision = decisions[0]
        for choice_index, choice in enumerate(main_decision["choices"]):
            key = (stage_index, ministry, choice_index)
            overview = literature_overviews[key]
            choice["literature_overview"] = overview
            choice["relevance"] = overview
            choice["ending_text"] = choice.get("outcome", "")
            if key in extra_dois:
                current = list(choice.get("dois", []) or [])
                for doi in extra_dois[key]:
                    if doi not in current:
                        current.append(doi)
                choice["dois"] = current

for phrase in (
    "The source matrix provides supporting literature for this outcome but does not include a separate relevance note in this row.",
    "The source matrix provides the papers for this branch without a separate relevance note.",
):
    app = app.replace(phrase, "")

# Keep the existing hover/focus citation structure, but make its language human and concise.
app = app.replace("Evidence from the source matrix", "Literature behind this ending")
app = app.replace("<strong>Why this outcome:</strong> ", "")
app = app.replace(
    "f'<div class=\"citation-section\"><strong>Supporting papers:</strong> {papers}</div>'",
    "''",
)
app = app.replace(
    "f'<div class=\"citation-section\"><strong>DOI links:</strong><br>{doi_html}</div>'",
    "f'<div class=\"citation-section\"><strong>Sources:</strong><br>{doi_html}</div>'",
)

# Remove either version of the instructional paragraph shown above the final result.
for sentence in (
    "This flowchart reconstructs the cabinet's actual decisions. Focus or hover an outcome to inspect the literature used for that consequence.",
    "The flowchart below follows the cabinet's three stages. Hover over or focus a large outcome node to see the literature and DOI links behind that consequence.",
):
    app = re.sub(
        r'\s*ui\.label\(\s*' + re.escape(repr(sentence)) + r'\s*\)\.classes\("lead"\)',
        "",
        app,
    )
    app = app.replace(sentence, "")

fate_block = '''            baseline = {"civilians": 130, "resources": 120, "popularity": 130, "nr": 130}
            resource_keys = ("civilians", "resources", "popularity", "nr")
            net_change = sum(int(room[key]) - baseline[key] for key in resource_keys)
            if net_change >= 0:
                fate_image = "/scenes/good-ending.webp"
                fate_title = "The Republic endures"
                fate_text = (
                    "The Republic comes through the AI crisis bruised but still governable. "
                    "The cabinet did not solve every problem, but the state retains enough capacity, trust and room to act "
                    "that the next government inherits a functioning republic rather than an emergency."
                )
            else:
                fate_image = "/scenes/bad-ending.webp"
                fate_title = "The Republic is under strain"
                fate_text = (
                    "The Republic survives the AI crisis, but it reaches the other side weaker than it entered. "
                    "The cabinet's trade-offs have accumulated into thinner public confidence, less room to manoeuvre "
                    "and institutions that will spend years repairing the damage."
                )

            with ui.element("section").classes("final-fate-card"):
                ui.image(fate_image).classes("final-fate-image")
                with ui.element("div").classes("final-fate-copy"):
                    ui.label("Fate of the Republic").classes("eyebrow")
                    ui.label(fate_title).classes("final-fate-title")
                    ui.label(fate_text).classes("final-fate-text")

'''
if "final-fate-card" not in app:
    anchor = '            with ui.element("div").classes("final-resource-strip"):'
    if anchor not in app:
        raise RuntimeError("Could not find final-resource-strip anchor")
    app = app.replace(anchor, fate_block + anchor, 1)

app = app.replace('ui.label("Outcome").classes("flow-kicker")', 'ui.label("Ending").classes("flow-kicker")')

fate_css = '''
.final-fate-card { display: grid; grid-template-columns: minmax(260px, .9fr) minmax(320px, 1.1fr); gap: 0; margin: 0 0 28px; border: 1px solid var(--line); background: #fff; overflow: hidden; }
.final-fate-image { width: 100%; height: 100%; min-height: 280px; object-fit: cover; }
.final-fate-copy { display: flex; flex-direction: column; justify-content: center; padding: 30px 34px; }
.final-fate-title { margin-top: 7px; color: var(--blue-dark); font-size: 30px; font-weight: 700; line-height: 1.1; }
.final-fate-text { margin-top: 14px; color: #343a40; font-size: 16px; line-height: 1.6; }
'''
if ".final-fate-card" not in css:
    marker = "/* Evidence-backed final flowchart */"
    css = css.replace(marker, marker + "\n" + fate_css, 1)
if "@media (max-width: 900px) {" in css and ".final-fate-card { grid-template-columns: 1fr; }" not in css:
    css = css.replace(
        "@media (max-width: 900px) {",
        "@media (max-width: 900px) {\n  .final-fate-card { grid-template-columns: 1fr; }\n  .final-fate-image { min-height: 220px; max-height: 420px; }",
        1,
    )

story_text = json.dumps(story, ensure_ascii=False, indent=2) + "\n"
packed_app = base64.b64encode(zlib.compress(app.encode("utf-8"), 9)).decode("ascii")
packed_story = base64.b64encode(zlib.compress(story_text.encode("utf-8"), 9)).decode("ascii")
packed_css = base64.b64encode(zlib.compress(css.encode("utf-8"), 9)).decode("ascii")

wrapper = re.sub(r"(?m)^_MAIN = '[^']+'$", "_MAIN = '" + packed_app + "'", wrapper, count=1)
wrapper = re.sub(r"(?m)^_STORY = '[^']+'$", "_STORY = '" + packed_story + "'", wrapper, count=1)
wrapper = re.sub(r"(?m)^_CSS = '[^']+'$", "_CSS = '" + packed_css + "'", wrapper, count=1)
path.write_text(wrapper, encoding="utf-8")

# Round-trip validation before committing.
test = path.read_text(encoding="utf-8")
for name in ("_MAIN", "_STORY", "_CSS"):
    m = re.search(rf"(?m)^{name} = '([^']+)'$", test)
    if not m:
        raise RuntimeError(f"Missing {name} after patch")
    zlib.decompress(base64.b64decode(m.group(1)))

decoded_story = json.loads(zlib.decompress(base64.b64decode(re.search(r"(?m)^_STORY = '([^']+)'$", test).group(1))))
assert sum(len(data["decisions"][m][0]["choices"]) for data in decoded_story["rounds"] for m in data["decisions"]) == 36
assert all(
    choice.get("literature_overview")
    for data in decoded_story["rounds"]
    for decisions in data["decisions"].values()
    for choice in decisions[0]["choices"]
)
print("Patched 36 policy endings, 2 overall Republic fates, and literature summaries.")
