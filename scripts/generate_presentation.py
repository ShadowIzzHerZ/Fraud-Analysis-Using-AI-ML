"""Generates a professional 6-slide widescreen (16:9) PowerPoint presentation
showcasing the Zen Fraud Operations Platform & ZenPay Android Application
with actual captured screenshots.
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# 16:9 Widescreen dimensions
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Brand Color Palette ("Warm Civic Minimal")
COLOR_BG = RGBColor(247, 245, 240)         # #f7f5f0 Warm background
COLOR_PRIMARY = RGBColor(184, 67, 30)      # #b8431e Terracotta accent
COLOR_PRIMARY_CONTAINER = RGBColor(255, 229, 222) # #ffe5de
COLOR_DARK = RGBColor(27, 28, 26)          # #1b1c1a Headline dark
COLOR_MUTED = RGBColor(100, 95, 88)        # Subtext muted
COLOR_CARD_BG = RGBColor(255, 255, 255)    # White card fill
COLOR_CARD_BORDER = RGBColor(229, 225, 216) # #e5e1d8 subtle border
COLOR_EMERALD = RGBColor(22, 163, 74)      # Green success
COLOR_ROSE = RGBColor(225, 29, 72)         # Rose danger

SCREENSHOT_DIR = os.path.abspath("docs/screenshots")

def add_bg(slide):
    """Fills slide background with warm civic minimal color."""
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = COLOR_BG
    bg_shape.line.fill.background()
    return bg_shape

def add_header(slide, tag: str, title: str, subtitle: str, slide_num: int):
    """Creates a consistent, elegant slide header."""
    # Tag chip
    chip = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.45), Inches(2.2), Inches(0.32))
    chip.fill.solid()
    chip.fill.fore_color.rgb = COLOR_PRIMARY_CONTAINER
    chip.line.color.rgb = COLOR_PRIMARY
    chip.line.width = Pt(1)
    tf = chip.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = tag.upper()
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY
    p.alignment = PP_ALIGN.CENTER

    # Title & Subtitle box
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.82), Inches(10.5), Inches(1.0))
    htf = header_box.text_frame
    htf.word_wrap = True
    htf.margin_left = htf.margin_right = htf.margin_top = htf.margin_bottom = 0
    
    tp = htf.paragraphs[0]
    tp.text = title
    tp.font.size = Pt(23)
    tp.font.bold = True
    tp.font.color.rgb = COLOR_DARK

    sp = htf.add_paragraph()
    sp.text = subtitle
    sp.font.size = Pt(12.5)
    sp.font.color.rgb = COLOR_MUTED

    # Slide Counter
    num_box = slide.shapes.add_textbox(Inches(11.8), Inches(0.45), Inches(0.8), Inches(0.4))
    ntf = num_box.text_frame
    np = ntf.paragraphs[0]
    np.text = f"0{slide_num} / 06"
    np.font.size = Pt(11)
    np.font.bold = True
    np.font.color.rgb = COLOR_MUTED
    np.alignment = PP_ALIGN.RIGHT

def create_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
    """Helper to draw clean rounded card container."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    if border_color:
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
    else:
        card.line.fill.background()
    return card

def build_presentation(output_path: str):
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: Title & Executive Overview
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_bg(s1)

    # Top Brand Badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.8), Inches(3.2), Inches(0.38))
    badge.fill.solid()
    badge.fill.fore_color.rgb = COLOR_PRIMARY_CONTAINER
    badge.line.color.rgb = COLOR_PRIMARY
    badge.line.width = Pt(1)
    btf = badge.text_frame
    bp = btf.paragraphs[0]
    bp.text = "● AI/ML FRAUD INTELLIGENCE · REAL-TIME"
    bp.font.size = Pt(10.5)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_PRIMARY
    bp.alignment = PP_ALIGN.CENTER

    # Title
    t_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.35), Inches(6.8), Inches(2.2))
    ttf = t_box.text_frame
    ttf.word_wrap = True
    tp1 = ttf.paragraphs[0]
    tp1.text = "Zen & ZenPay"
    tp1.font.size = Pt(40)
    tp1.font.bold = True
    tp1.font.color.rgb = COLOR_DARK

    tp2 = ttf.add_paragraph()
    tp2.text = "Autonomous Fraud Defense & Real-Time Payment Security"
    tp2.font.size = Pt(21)
    tp2.font.bold = True
    tp2.font.color.rgb = COLOR_PRIMARY

    # Overview bullets / description
    desc_box = s1.shapes.add_textbox(Inches(0.8), Inches(3.6), Inches(6.4), Inches(2.2))
    dtf = desc_box.text_frame
    dtf.word_wrap = True
    
    bullets = [
        ("Sub-Millisecond Scoring", "Evaluates velocity, amount outliers, impossible travel, and mule patterns live."),
        ("Synchronized Native Ecosystem", "Standalone ZenPay Android client (P2P + UPI) connected to SOC web console."),
        ("Autonomous Enforcement", "Zero-latency auto-freeze engine halting compromised instruments in < 40ms."),
        ("Audit-Ready Observability", "Complete trace telemetry, case dossiers, and analyst review workflow.")
    ]
    for i, (head, body) in enumerate(bullets):
        p = dtf.paragraphs[0] if i == 0 else dtf.add_paragraph()
        p.text = f"•  {head}: "
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_DARK
        
        run = p.add_run()
        run.text = body
        run.font.bold = False
        run.font.size = Pt(11.5)
        run.font.color.rgb = COLOR_MUTED

    # Highlights strip at bottom
    hl_card = create_card(s1, Inches(0.8), Inches(5.9), Inches(6.4), Inches(1.0))
    htf = hl_card.text_frame
    hp = htf.paragraphs[0]
    hp.text = "PRODUCTION-READY HYBRID STACK"
    hp.font.size = Pt(10)
    hp.font.bold = True
    hp.font.color.rgb = COLOR_PRIMARY
    
    hp2 = htf.add_paragraph()
    hp2.text = "Python (NiceGUI + FastAPI + Asyncio)  |  Kotlin Native Android  |  Cloudflare Tunnel  |  Supabase Auth"
    hp2.font.size = Pt(11)
    hp2.font.color.rgb = COLOR_DARK

    # Right side: Combined Visual Showcase (Web Console + Android Phone)
    create_card(s1, Inches(7.5), Inches(0.8), Inches(5.0), Inches(5.9))
    
    # Web preview on top
    web_img_path = os.path.join(SCREENSHOT_DIR, "web_console.png")
    if os.path.exists(web_img_path):
        s1.shapes.add_picture(web_img_path, Inches(7.65), Inches(1.0), width=Inches(4.7))
    
    # Android preview floating over bottom right
    phone_img_path = os.path.join(SCREENSHOT_DIR, "app_home.png")
    if os.path.exists(phone_img_path):
        s1.shapes.add_picture(phone_img_path, Inches(10.5), Inches(3.2), height=Inches(3.3))

    # Small caption
    cap_box = s1.shapes.add_textbox(Inches(7.65), Inches(6.25), Inches(3.0), Inches(0.4))
    ctf = cap_box.text_frame
    cp = ctf.paragraphs[0]
    cp.text = "Live Console & Mobile Simulator"
    cp.font.size = Pt(10)
    cp.font.bold = True
    cp.font.color.rgb = COLOR_MUTED

    # =========================================================================
    # SLIDE 2: ZenPay Android Mobile App — Native P2P & Wallet Transfers
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_bg(s2)
    add_header(s2, "Mobile Client", "ZenPay Android: User-to-User P2P & UPI Simulation",
               "Native Kotlin client supporting wallet management, direct ID transfers, and camera QR scanning.", 2)

    # Phone Screen 1: Home
    create_card(s2, Inches(0.8), Inches(1.9), Inches(2.6), Inches(5.1))
    if os.path.exists(phone_img_path):
        s2.shapes.add_picture(phone_img_path, Inches(0.9), Inches(2.0), height=Inches(4.9))

    # Phone Screen 2: My QR
    qr_img_path = os.path.join(SCREENSHOT_DIR, "app_myqr.png")
    create_card(s2, Inches(3.7), Inches(1.9), Inches(2.6), Inches(5.1))
    if os.path.exists(qr_img_path):
        s2.shapes.add_picture(qr_img_path, Inches(3.8), Inches(2.0), height=Inches(4.9))

    # Right Content Cards (3 feature cards)
    c1 = create_card(s2, Inches(6.6), Inches(1.9), Inches(5.9), Inches(1.55))
    ctf1 = c1.text_frame
    ctf1.word_wrap = True
    p1 = ctf1.paragraphs[0]
    p1.text = "1. Device-Generated ZenPay Wallet ID"
    p1.font.bold = True
    p1.font.size = Pt(14)
    p1.font.color.rgb = COLOR_PRIMARY
    p1_sub = ctf1.add_paragraph()
    p1_sub.text = "Generates a persistent 15-digit wallet identity on first launch. Users can share their formatted ID or display a dynamic QR code for immediate peer transfers."
    p1_sub.font.size = Pt(11)
    p1_sub.font.color.rgb = COLOR_DARK

    c2 = create_card(s2, Inches(6.6), Inches(3.65), Inches(5.9), Inches(1.55))
    ctf2 = c2.text_frame
    ctf2.word_wrap = True
    p2 = ctf2.paragraphs[0]
    p2.text = "2. Offline-First & Cloud Sync Architecture"
    p2.font.bold = True
    p2.font.size = Pt(14)
    p2.font.color.rgb = COLOR_PRIMARY
    p2_sub = ctf2.add_paragraph()
    p2_sub.text = "Functions completely local with standalone device-side Luhn checks and fallback scoring, but connects to the Cloudflare tunnel for live telemetry sync to the fraud ops desk."
    p2_sub.font.size = Pt(11)
    p2_sub.font.color.rgb = COLOR_DARK

    c3 = create_card(s2, Inches(6.6), Inches(5.4), Inches(5.9), Inches(1.55))
    ctf3 = c3.text_frame
    ctf3.word_wrap = True
    p3 = ctf3.paragraphs[0]
    p3.text = "3. Sandbox Safety Guarantee"
    p3.font.bold = True
    p3.font.size = Pt(14)
    p3.font.color.rgb = COLOR_PRIMARY
    p3_sub = ctf3.add_paragraph()
    p3_sub.text = "Only accepts verified sandbox test PANs (Stripe/Razorpay test-sets) and stamps payee handles with non-resolvable '@fakebank' domains, guaranteeing no real money can ever move."
    p3_sub.font.size = Pt(11)
    p3_sub.font.color.rgb = COLOR_DARK

    # =========================================================================
    # SLIDE 3: On-Device Fraud Scoring & Audit History
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_bg(s3)
    add_header(s3, "Transaction Intelligence", "Mobile Audit Trail & Real-Time Risk Feedback",
               "Every transaction is scored and badged with instant explanation chips before analyst review.", 3)

    # Phone Screen: History
    hist_img_path = os.path.join(SCREENSHOT_DIR, "app_history.png")
    create_card(s3, Inches(0.8), Inches(1.9), Inches(2.6), Inches(5.1))
    if os.path.exists(hist_img_path):
        s3.shapes.add_picture(hist_img_path, Inches(0.9), Inches(2.0), height=Inches(4.9))

    # Middle Card: How Android app scores payments
    c_score = create_card(s3, Inches(3.7), Inches(1.9), Inches(4.3), Inches(5.1))
    stf = c_score.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.text = "Real-Time Scoring Flow"
    sp.font.bold = True
    sp.font.size = Pt(15)
    sp.font.color.rgb = COLOR_PRIMARY

    steps = [
        ("Step 1: Input & Sanitization", "Validates 16-digit PAN via Luhn algorithm, checks expiry & CVV formatting."),
        ("Step 2: Local Rule Evaluation", "Matches against local device velocity windows and abnormal transfer amounts."),
        ("Step 3: Portal Cloud Dispatch", "Dispatches transaction asynchronously to /api/portal/pay via HTTP/2 tunnel."),
        ("Step 4: Composite Risk Scoring", "Receives unified 0.00-1.00 risk score and detector firing rationales."),
        ("Step 5: Audit Trail Archival", "Stores timestamped receipt in Room/JSON local history store with color badges.")
    ]
    for step_title, step_desc in steps:
        p = stf.add_paragraph()
        p.text = f"• {step_title}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_DARK
        p_sub = stf.add_paragraph()
        p_sub.text = step_desc
        p_sub.font.size = Pt(9.5)
        p_sub.font.color.rgb = COLOR_MUTED

    # Right Card: Actual Live Transaction Breakdown (From Phone Screenshot)
    c_live = create_card(s3, Inches(8.3), Inches(1.9), Inches(4.2), Inches(5.1))
    ltf = c_live.text_frame
    ltf.word_wrap = True
    lp = ltf.paragraphs[0]
    lp.text = "Observed Transaction Logs"
    lp.font.bold = True
    lp.font.size = Pt(15)
    lp.font.color.rgb = COLOR_PRIMARY

    tx_samples = [
        ("ZenPay Demo Kirana Store", "₹499.00", "Processed — no risk signals · 0.00", COLOR_EMERALD),
        ("Sent to •••5555 (Rapid Transfer)", "₹10,000.00", "Risk score flagged · 0.18", COLOR_PRIMARY),
        ("Sent to •••5555 (Micro-probe)", "₹10.00", "Processed — no risk signals · 0.00", COLOR_EMERALD),
        ("Sent to •••2345 (P2P Wallet)", "₹1,000.00", "Processed — no risk signals · 0.00", COLOR_EMERALD),
    ]
    for title, amt, status, color in tx_samples:
        p = ltf.add_paragraph()
        p.text = f"{title} — {amt}"
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = COLOR_DARK
        
        ps = ltf.add_paragraph()
        ps.text = f"Status: {status}"
        ps.font.bold = True
        ps.font.size = Pt(9.5)
        ps.font.color.rgb = color

    # Bottom summary in right card
    p_sum = ltf.add_paragraph()
    p_sum.text = "\nImmediate Analyst Sync:"
    p_sum.font.bold = True
    p_sum.font.size = Pt(11)
    p_sum.font.color.rgb = COLOR_DARK

    p_sum_desc = ltf.add_paragraph()
    p_sum_desc.text = "Every transaction triggered on mobile reflects within 50ms across the SOC dashboard feed and alerts queue."
    p_sum_desc.font.size = Pt(9.5)
    p_sum_desc.font.color.rgb = COLOR_MUTED

    # =========================================================================
    # SLIDE 4: Zen Web Platform — Landing & Secure Analyst Access
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_bg(s4)
    add_header(s4, "Web Platform", "Zen Public Portal: High-Conversion Marketing & Auth",
               "Designed with Warm Civic Minimal aesthetics, lightweight typography, and PKCE OAuth.", 4)

    # Large Landing Page Screenshot Card
    create_card(s4, Inches(0.8), Inches(1.9), Inches(7.5), Inches(5.1))
    landing_img = os.path.join(SCREENSHOT_DIR, "web_landing.png")
    if os.path.exists(landing_img):
        s4.shapes.add_picture(landing_img, Inches(0.95), Inches(2.05), width=Inches(7.2))

    # Right side 3 Callouts
    rc1 = create_card(s4, Inches(8.6), Inches(1.9), Inches(3.9), Inches(1.55))
    rtf1 = rc1.text_frame
    rtf1.word_wrap = True
    rp1 = rtf1.paragraphs[0]
    rp1.text = "Warm Civic Minimal Visual System"
    rp1.font.bold = True
    rp1.font.size = Pt(13)
    rp1.font.color.rgb = COLOR_PRIMARY
    rp1_s = rtf1.add_paragraph()
    rp1_s.text = "Tailwind arbitrary values over Quasar base, Plus Jakarta Sans typography, and subtle terracotta accents replacing generic dark-ops dashboards."
    rp1_s.font.size = Pt(10)
    rp1_s.font.color.rgb = COLOR_DARK

    rc2 = create_card(s4, Inches(8.6), Inches(3.65), Inches(3.9), Inches(1.55))
    rtf2 = rc2.text_frame
    rtf2.word_wrap = True
    rp2 = rtf2.paragraphs[0]
    rp2.text = "Enterprise PKCE Google OAuth"
    rp2.font.bold = True
    rp2.font.size = Pt(13)
    rp2.font.color.rgb = COLOR_PRIMARY
    rp2_s = rtf2.add_paragraph()
    rp2_s.text = "Supabase Auth with custom public.zen_analysts routing trigger, hand-rolled PKCE code-exchange handshake, and mobile deep-link redirection."
    rp2_s.font.size = Pt(10)
    rp2_s.font.color.rgb = COLOR_DARK

    rc3 = create_card(s4, Inches(8.6), Inches(5.4), Inches(3.9), Inches(1.55))
    rtf3 = rc3.text_frame
    rtf3.word_wrap = True
    rp3 = rtf3.paragraphs[0]
    rp3.text = "Zero Leak Responsive Geometry"
    rp3.font.bold = True
    rp3.font.size = Pt(13)
    rp3.font.color.rgb = COLOR_PRIMARY
    rp3_s = rtf3.add_paragraph()
    rp3_s.text = "Flex-1 stretch architecture and max-w-[100vw] bounds preventing right-side gutters on desktop monitors while scaling seamlessly down to 360px phones."
    rp3_s.font.size = Pt(10)
    rp3_s.font.color.rgb = COLOR_DARK

    # =========================================================================
    # SLIDE 5: SOC Live Operations Console & Attack Injection
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_bg(s5)
    add_header(s5, "SOC Console", "Live Ingestion Stream & Real-Time Attack Simulation",
               "High-throughput WebSocket feed processing 450+ events/min with instant manual scenario injection.", 5)

    # Large Console Screenshot Card
    create_card(s5, Inches(0.8), Inches(1.9), Inches(7.5), Inches(5.1))
    if os.path.exists(web_img_path):
        s5.shapes.add_picture(web_img_path, Inches(0.95), Inches(2.05), width=Inches(7.2))

    # Right side 3 Operations Highlights
    oc1 = create_card(s5, Inches(8.6), Inches(1.9), Inches(3.9), Inches(1.55))
    otf1 = oc1.text_frame
    otf1.word_wrap = True
    op1 = otf1.paragraphs[0]
    op1.text = "Real-Time Telemetry & Throughput"
    op1.font.bold = True
    op1.font.size = Pt(13)
    op1.font.color.rgb = COLOR_PRIMARY
    op1_s = otf1.add_paragraph()
    op1_s.text = "Monitors 450+ transactions/min with 18ms server latency, live rule engine capacity utilization, and rolling 15-minute value-at-risk indicators."
    op1_s.font.size = Pt(10)
    op1_s.font.color.rgb = COLOR_DARK

    oc2 = create_card(s5, Inches(8.6), Inches(3.65), Inches(3.9), Inches(1.55))
    otf2 = oc2.text_frame
    otf2.word_wrap = True
    op2 = otf2.paragraphs[0]
    op2.text = "One-Click Attack Injection"
    op2.font.bold = True
    op2.font.size = Pt(13)
    op2.font.color.rgb = COLOR_PRIMARY
    op2_s = otf2.add_paragraph()
    op2_s.text = "Allows analysts to stress-test detection pipelines by injecting pre-timed fraud patterns: Velocity Spikes, Amount Outliers, Impossible Travel, and Mule Bursts."
    op2_s.font.size = Pt(10)
    op2_s.font.color.rgb = COLOR_DARK

    oc3 = create_card(s5, Inches(8.6), Inches(5.4), Inches(3.9), Inches(1.55))
    otf3 = oc3.text_frame
    otf3.word_wrap = True
    op3 = otf3.paragraphs[0]
    op3.text = "Emergency Freeze Circuit Breaker"
    op3.font.bold = True
    op3.font.size = Pt(13)
    op3.font.color.rgb = COLOR_PRIMARY
    op3_s = otf3.add_paragraph()
    op3_s.text = "Global emergency action instantly halts transactions scoring >= 0.80 across all channels (Online CNP, In-Store POS, UPI, P2P) to contain active outbreaks."
    op3_s.font.size = Pt(10)
    op3_s.font.color.rgb = COLOR_DARK

    # =========================================================================
    # SLIDE 6: Automated Policy Rules & Flagged Alerts Queue
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_bg(s6)
    add_header(s6, "Policy & Defense", "Automated Detection Rules & Flagged Alerts Queue",
               "Multi-engine scoring architecture, configurable auto-freeze thresholds, and full analyst dossier review.", 6)

    # Top Left Image: Policies
    create_card(s6, Inches(0.8), Inches(1.9), Inches(5.7), Inches(2.45))
    policies_img = os.path.join(SCREENSHOT_DIR, "web_policies.png")
    if os.path.exists(policies_img):
        s6.shapes.add_picture(policies_img, Inches(0.9), Inches(2.0), width=Inches(5.5))

    # Bottom Left Image: Alerts Queue
    create_card(s6, Inches(0.8), Inches(4.55), Inches(5.7), Inches(2.45))
    alerts_img = os.path.join(SCREENSHOT_DIR, "web_alerts.png")
    if os.path.exists(alerts_img):
        s6.shapes.add_picture(alerts_img, Inches(0.9), Inches(4.65), width=Inches(5.5))

    # Right Content Box: 6 Detection Engines Breakdown
    det_card = create_card(s6, Inches(6.8), Inches(1.9), Inches(5.7), Inches(5.1))
    dtf = det_card.text_frame
    dtf.word_wrap = True
    dp = dtf.paragraphs[0]
    dp.text = "The 6 Core Detection Engines"
    dp.font.bold = True
    dp.font.size = Pt(15)
    dp.font.color.rgb = COLOR_PRIMARY

    engines = [
        ("Velocity Spike (Max Weight +0.55)", "Flags rapid card reuse (5-9+ transactions within 60s), catching credential stuffing and automated bot script attacks."),
        ("Impossible Travel (Max Weight +0.50)", "Haversine geodesic distance calculation between sequential transactions, flagging supersonic location hops (e.g. 3,000,000 km/h)."),
        ("Mule Burst Ring (Max Weight +0.45)", "Identifies card fanning small rapid sums across multiple distinct merchants/payees, a classic money-mule laundering signature."),
        ("Amount Outlier (Max Weight +0.45)", "Online Welford's algorithm tracking running mean and variance in log-space, robust to natural right-skewed spending behaviors."),
        ("New Device Fingerprint (Max Weight +0.25)", "Detects novel client fingerprints paired with above-average transaction sums."),
        ("Unusual Category / MCC (Max Weight +0.12)", "Flags merchant category codes never before encountered in cardholder history.")
    ]
    for eng_title, eng_desc in engines:
        p = dtf.add_paragraph()
        p.text = f"• {eng_title}"
        p.font.bold = True
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_DARK
        
        p_sub = dtf.add_paragraph()
        p_sub.text = eng_desc
        p_sub.font.size = Pt(9)
        p_sub.font.color.rgb = COLOR_MUTED

    # Save presentation
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    prs.save(output_path)
    print(f"Successfully generated 6-slide presentation at: {output_path}")

if __name__ == "__main__":
    output_pptx = "docs/Zen_Fraud_Analysis_Platform.pptx"
    build_presentation(output_pptx)
