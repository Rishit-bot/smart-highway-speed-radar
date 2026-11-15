"""
Ticket Generator Module.
Generates official, high-resolution electronic citation documents (E-Tickets)
using OpenCV and Pillow (PIL).
Includes mathematical overlays, radar HUD telemetry, illustrative evidence,
and cryptographic/barcode identification.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import config
from backend.storage import JSONDatabase


class TicketGenerator:
    """
    Object-Oriented Citation Image Generator.
    Combines OpenCV for computer vision radar HUD overlays and Pillow
    for typography, structured tabular styling, and official enforcement seals.
    """

    def __init__(self, db: Optional[JSONDatabase] = None):
        from backend.storage import db as default_db
        self.db = db or default_db
        self.output_dir = Path(config.GENERATED_TICKETS_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Fonts
        self._font_title = self._load_font(26, bold=True)
        self._font_header = self._load_font(18, bold=True)
        self._font_body = self._load_font(14, bold=False)
        self._font_bold = self._load_font(14, bold=True)
        self._font_small = self._load_font(11, bold=False)
        self._font_fine = self._load_font(24, bold=True)

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Attempt to load clean system TrueType font, falling back to default."""
        font_names = [
            "arialbd.ttf" if bold else "arial.ttf",
            "segoeuib.ttf" if bold else "segoeui.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "tahoma.ttf",
            "calibri.ttf"
        ]
        # Common Windows font directories
        win_fonts = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"

        for fn in font_names:
            fp = win_fonts / fn
            if fp.exists():
                try:
                    return ImageFont.truetype(str(fp), size)
                except Exception:
                    continue

        try:
            return ImageFont.load_default()
        except Exception:
            return None

    def create_illustrative_radar_snapshot(
        self,
        vehicle_id: int,
        vehicle_class: int,
        speed: float,
        speed_limit: float,
        timestamp: str
    ) -> np.ndarray:
        """
        Synthesizes an illustrative high-angle highway radar camera frame using OpenCV.
        Draws highway lanes, simulated vehicle footprint, radar target reticle,
        bounding box with velocity label, and mandatory academic disclaimer.
        """
        # 640x360 CCTV frame
        w, h = 640, 360
        # Dark asphalt / night highway CCTV palette (BGR)
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (22, 26, 32)  # Dark slate background

        # Draw perspective highway lanes
        cv2.line(frame, (80, h), (260, 40), (60, 70, 85), 2)    # Left shoulder
        cv2.line(frame, (240, h), (300, 40), (80, 95, 115), 1)  # Lane 1 dashed
        cv2.line(frame, (400, h), (340, 40), (80, 95, 115), 1)  # Lane 2 dashed
        cv2.line(frame, (560, h), (380, 40), (60, 70, 85), 2)   # Right shoulder

        # Horizon / highway lights
        cv2.line(frame, (0, 40), (w, 40), (40, 45, 55), 1)
        for lx in [270, 310, 350]:
            cv2.circle(frame, (lx, 38), 3, (120, 180, 255), -1)

        # Vehicle representation based on class
        # Center of detection box
        cx, cy = 320, 200
        if vehicle_class == 1:  # Motorcycle
            bw, bh = 50, 70
            veh_color = (200, 140, 50)  # Cyan/Blue tone
        elif vehicle_class == 3:  # Truck
            bw, bh = 140, 150
            veh_color = (120, 130, 140)
        else:  # Sedan
            bw, bh = 100, 110
            veh_color = (180, 90, 70)

        # Draw simulated vehicle body
        vx1, vy1 = cx - (bw // 2), cy - (bh // 2)
        vx2, vy2 = cx + (bw // 2), cy + (bh // 2)
        cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (45, 50, 60), -1)
        cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (90, 100, 120), 2)

        # Windshield / Roof geometry
        cv2.rectangle(frame, (vx1 + 10, vy1 + 15), (vx2 - 10, vy2 - 35), (25, 30, 38), -1)
        # Headlights / Taillights (red rear lights)
        cv2.circle(frame, (vx1 + 12, vy2 - 8), 6, (40, 40, 220), -1)
        cv2.circle(frame, (vx2 - 12, vy2 - 8), 6, (40, 40, 220), -1)

        # Radar targeting HUD box (Electric Cyan / Red if violation)
        hud_color = (50, 50, 235) if speed > speed_limit else (235, 180, 40)  # Red BGR vs Cyan BGR
        cv2.rectangle(frame, (vx1 - 10, vy1 - 10), (vx2 + 10, vy2 + 10), hud_color, 2)

        # Corner reticles
        corner_len = 16
        for pt in [(vx1 - 10, vy1 - 10), (vx2 + 10, vy1 - 10), (vx1 - 10, vy2 + 10), (vx2 + 10, vy2 + 10)]:
            px, py = pt
            dx = corner_len if px < cx else -corner_len
            dy = corner_len if py < cy else -corner_len
            cv2.line(frame, (px, py), (px + dx, py), hud_color, 2)
            cv2.line(frame, (px, py), (px, py + dy), hud_color, 2)

        # Radar crosshair in center
        cv2.drawMarker(frame, (cx, cy), hud_color, cv2.MARKER_CROSS, 20, 1)

        # HUD Text Overlay: Vehicle ID & Recorded Velocity
        tag_text = f"TARGET #{vehicle_id:04d} | {speed:.1f} KM/H"
        cv2.putText(frame, tag_text, (vx1 - 10, vy1 - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, hud_color, 2)

        # Camera Header Bar
        cv2.rectangle(frame, (0, 0), (w, 32), (10, 12, 16), -1)
        cv2.putText(frame, f"CAM-04 NORTHBOUND [CH-101] | {timestamp}", (12, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 195, 210), 1)

        # Prominent Academic / NGSIM illustrative watermark banner
        disclaimer = "ILLUSTRATIVE EVIDENCE - NGSIM ACADEMIC SIMULATION"
        cv2.rectangle(frame, (0, h - 28), (w, h), (15, 18, 22), -1)
        cv2.putText(frame, disclaimer, (80, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 220, 255), 1)

        return frame

    def draw_barcode_matrix(self, draw: ImageDraw.ImageDraw, x: int, y: int, code: str, width: int = 180, height: int = 40):
        """Draw a realistic synthetic 1D barcode on citation canvas."""
        # Clean pseudo barcode lines from code hash
        hash_val = hash(code)
        curr_x = x
        for i in range(45):
            bit = (hash_val >> (i % 30)) & 1
            bar_w = 2 if bit else 4
            if curr_x + bar_w > x + width:
                break
            # draw line
            draw.rectangle([curr_x, y, curr_x + bar_w - 1, y + height], fill=(30, 40, 55))
            curr_x += bar_w + (2 if (i % 2 == 0) else 1)
        # Barcode code string below
        draw.text((x + 10, y + height + 3), f"*{code}*", fill=(90, 105, 125), font=self._font_small)

    def draw_official_seal(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int = 40):
        """Draw an official digital seal emblem."""
        # Outer double circle
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(0, 180, 230), width=2)
        draw.ellipse([cx - radius + 4, cy - radius + 4, cx + radius - 4, cy + radius - 4], outline=(0, 140, 190), width=1)
        # Inner text / emblem
        draw.text((cx - 24, cy - 14), "STATE", fill=(0, 200, 255), font=self._font_small)
        draw.text((cx - 27, cy - 2), "HIGHWAY", fill=(0, 200, 255), font=self._font_small)
        draw.text((cx - 28, cy + 10), "PATROL", fill=(0, 200, 255), font=self._font_small)

    def overlay_vehicle_details(
        self,
        canvas: Image.Image,
        violation: Dict[str, Any],
        ticket_id: str,
        settings: Dict[str, Any]
    ) -> Image.Image:
        """
        Assembles all violation data, telemetry, monetary fine calculations,
        and evidence photo into a structured citation canvas.
        """
        draw = ImageDraw.Draw(canvas)
        w, h = canvas.size

        # Color Palette
        NAVY_DARK = (13, 20, 36)
        PANEL_BG = (22, 33, 58)
        BORDER_COLOR = (42, 60, 95)
        ACCENT_CYAN = (0, 230, 255)
        ACCENT_RED = (255, 75, 75)
        TEXT_LIGHT = (240, 245, 255)
        TEXT_MUTED = (145, 165, 195)
        HIGHLIGHT_YELLOW = (255, 200, 50)

        # 1. Background Fill
        draw.rectangle([0, 0, w, h], fill=NAVY_DARK)

        # 2. Outer Border Frame
        draw.rectangle([16, 16, w - 16, h - 16], outline=BORDER_COLOR, width=2)
        draw.rectangle([20, 20, w - 20, h - 20], outline=(25, 45, 75), width=1)

        # 3. Header Banner
        draw.rectangle([22, 22, w - 22, 110], fill=(18, 27, 48))
        draw.line([22, 110, w - 22, 110], fill=ACCENT_CYAN, width=2)

        # Header Titles
        draw.text((40, 35), "STATE HIGHWAY PATROL • AUTOMATED ENFORCEMENT DIVISION",
                  fill=ACCENT_CYAN, font=self._font_small)
        draw.text((40, 52), "NOTICE OF SPEEDING VIOLATION & E-CITATION",
                  fill=TEXT_LIGHT, font=self._font_title)
        draw.text((40, 84), "OFFICIAL CITATION ISSUED PURSUANT TO AUTOMATED SPEED RADAR MONITORING",
                  fill=TEXT_MUTED, font=self._font_small)

        # Draw Official Seal in Header Right
        self.draw_official_seal(draw, w - 85, 66, radius=34)

        # 4. Top Information Badges (Ticket ID, Status, Date)
        badge_y = 125
        # Ticket ID Badge
        draw.rectangle([40, badge_y, 250, badge_y + 44], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
        draw.text((50, badge_y + 6), "CITATION NUMBER", fill=TEXT_MUTED, font=self._font_small)
        draw.text((50, badge_y + 20), ticket_id, fill=HIGHLIGHT_YELLOW, font=self._font_bold)

        # Violation Code Badge
        vio_id = violation.get("violation_id", "VIO-0000")
        draw.rectangle([265, badge_y, 475, badge_y + 44], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
        draw.text((275, badge_y + 6), "VIOLATION CODE", fill=TEXT_MUTED, font=self._font_small)
        draw.text((275, badge_y + 20), vio_id, fill=TEXT_LIGHT, font=self._font_bold)

        # Date & Timestamp Badge
        ts = violation.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        draw.rectangle([490, badge_y, w - 40, badge_y + 44], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
        draw.text((500, badge_y + 6), "DATE & TIME OF INFRACTION", fill=TEXT_MUTED, font=self._font_small)
        draw.text((500, badge_y + 20), ts, fill=TEXT_LIGHT, font=self._font_bold)

        # 5. Middle Split: Left Details Table (w=420), Right Evidence Image (w=460)
        table_top = 185

        # Table Panel Box
        draw.rectangle([40, table_top, 450, table_top + 340], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
        # Table Header
        draw.rectangle([40, table_top, 450, table_top + 36], fill=(28, 42, 72))
        draw.text((54, table_top + 10), "VIOLATION & TELEMETRY BREAKDOWN", fill=ACCENT_CYAN, font=self._font_bold)

        # Data rows
        v_id = violation.get("vehicle_id", 0)
        v_class = violation.get("vehicle_class", 2)
        v_class_name = config.VEHICLE_CLASS_MAP.get(v_class, f"Class {v_class}")
        rec_speed = float(violation.get("recorded_speed", 0.0))
        speed_limit = float(violation.get("speed_limit", settings.get("speed_limit", 80.0)))
        excess_speed = float(violation.get("excess_speed", max(0.0, rec_speed - speed_limit)))
        fine = float(violation.get("fine", 0.0))
        currency = settings.get("currency_symbol", "$")
        unit = settings.get("unit", "km/h")
        camera_id = settings.get("camera_id", "RADAR-HWY-101-N")
        location = settings.get("location_name", "Interstate 80 / US-101 Corridor")

        rows = [
            ("Vehicle Identifier (NGSIM):", f"#{v_id}"),
            ("Vehicle Classification:", v_class_name),
            ("Enforcement Radar Sensor:", camera_id),
            ("Monitoring Checkpoint:", location),
            ("Posted Speed Limit:", f"{speed_limit:.1f} {unit}"),
            ("Recorded Velocity:", f"{rec_speed:.1f} {unit}"),
            ("Excess Speed Above Limit:", f"+{excess_speed:.1f} {unit}"),
            ("Base Penalty Rate:", f"{currency}{settings.get('base_fine', 500.0):.2f}"),
            ("Rate Per Excess km/h:", f"{currency}{settings.get('fine_per_kmh', 50.0):.2f} / {unit}")
        ]

        row_y = table_top + 45
        for label, val in rows:
            draw.text((54, row_y), label, fill=TEXT_MUTED, font=self._font_small)
            # Highlight excess speed in bold red
            val_color = ACCENT_RED if "Excess" in label else (ACCENT_CYAN if "Recorded" in label else TEXT_LIGHT)
            draw.text((260, row_y), val, fill=val_color, font=self._font_bold if ("Excess" in label or "Recorded" in label) else self._font_body)
            # Row divider line
            draw.line([54, row_y + 26, 436, row_y + 26], fill=(30, 45, 75), width=1)
            row_y += 31

        # 6. Right Side: Radar Photographic Evidence
        evidence_x = 475
        evidence_y = table_top
        evidence_w = 445
        evidence_h = 250

        draw.rectangle([evidence_x, evidence_y, evidence_x + evidence_w, evidence_y + evidence_h],
                       fill=(10, 15, 25), outline=BORDER_COLOR, width=1)

        # Generate and paste illustrative radar evidence image
        cv_img = self.create_illustrative_radar_snapshot(
            vehicle_id=v_id,
            vehicle_class=v_class,
            speed=rec_speed,
            speed_limit=speed_limit,
            timestamp=ts
        )
        # Convert OpenCV BGR to RGB PIL
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_evidence = Image.fromarray(rgb_img)
        # Resize to fit box
        pil_evidence_resized = pil_evidence.resize((evidence_w - 4, evidence_h - 4), Image.Resampling.LANCZOS)
        canvas.paste(pil_evidence_resized, (evidence_x + 2, evidence_y + 2))

        # 7. Penalty Summary Card below Evidence (Right Bottom)
        fine_box_y = evidence_y + evidence_h + 12
        fine_box_h = 78
        draw.rectangle([evidence_x, fine_box_y, evidence_x + evidence_w, fine_box_y + fine_box_h],
                       fill=(35, 22, 28), outline=ACCENT_RED, width=2)
        draw.text((evidence_x + 18, fine_box_y + 12), "TOTAL SIMULATED PENALTY DUE:",
                  fill=(255, 170, 170), font=self._font_small)
        fine_str = f"{currency}{fine:,.2f}"
        draw.text((evidence_x + 18, fine_box_y + 30), fine_str, fill=ACCENT_RED, font=self._font_fine)
        draw.text((evidence_x + 240, fine_box_y + 40), "DUE WITHIN 30 DAYS", fill=TEXT_MUTED, font=self._font_small)

        # 8. Bottom Section: Barcode, Legal Disclaimer, Authenticity Signature
        bottom_y = 545
        # Barcode
        self.draw_barcode_matrix(draw, 50, bottom_y, f"{ticket_id}-{v_id}", width=220, height=40)

        # Legal & Academic Notice Box
        legal_text = (
            "NOTICE: This document is an academic computer vision demonstration generated by the Smart Highway\n"
            "Radar System. Speeds calculated from NGSIM trajectory telemetry. Evidence photography is illustrative.\n"
            "For inquiries or citation dispute, contact the Department of Transportation Automated Enforcement Unit."
        )
        draw.text((300, bottom_y), legal_text, fill=(120, 140, 170), font=self._font_small)

        # Digital Signature Stamp
        draw.text((w - 200, bottom_y + 28), "ELECTRONIC SIGNATURE VERIFIED", fill=ACCENT_CYAN, font=self._font_small)
        draw.line([w - 200, bottom_y + 43, w - 40, bottom_y + 43], fill=ACCENT_CYAN, width=1)
        draw.text((w - 200, bottom_y + 46), f"OFFICER ID: AUTO-RADAR-{camera_id[-4:]}", fill=TEXT_MUTED, font=self._font_small)

        return canvas

    def generate_ticket(self, violation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate full electronic citation document for a detected violation.
        Saves output PNG to generated_tickets/ and returns record dictionary.
        Prevents duplicate ticket generation.
        """
        v_id = int(violation.get("vehicle_id", 0))
        ticket_id = f"TKT-2026-{v_id:04d}"

        # Check if ticket already exists
        existing = self.db.get_ticket_by_id(ticket_id)
        if existing:
            return existing

        settings = self.db.get_settings()

        # Canvas Dimensions: High-Res 960 x 640
        canvas_w, canvas_h = 960, 640
        blank_canvas = Image.new("RGB", (canvas_w, canvas_h), color=(13, 20, 36))

        # Render overlay details
        ticket_canvas = self.overlay_vehicle_details(
            canvas=blank_canvas,
            violation=violation,
            ticket_id=ticket_id,
            settings=settings
        )

        # Save ticket image file
        filename = f"{ticket_id}.png"
        output_file_path = self.output_dir / filename
        self.save_ticket(ticket_canvas, output_file_path)

        # Construct ticket database record
        v_class = violation.get("vehicle_class", 2)
        v_class_name = config.VEHICLE_CLASS_MAP.get(v_class, f"Class {v_class}")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ticket_record = {
            "ticket_id": ticket_id,
            "violation_id": violation.get("violation_id", f"VIO-{v_id:04d}"),
            "vehicle_id": v_id,
            "vehicle_class_name": v_class_name,
            "recorded_speed": float(violation.get("recorded_speed", 0.0)),
            "speed_limit": float(violation.get("speed_limit", settings.get("speed_limit", 80.0))),
            "excess_speed": float(violation.get("excess_speed", 0.0)),
            "fine": float(violation.get("fine", 0.0)),
            "image_path": str(Path("generated_tickets") / filename),
            "created_at": created_at,
            "status": "ISSUED"
        }

        # Store in persistent database
        self.db.add_ticket(ticket_record)

        return ticket_record

    def save_ticket(self, canvas: Image.Image, file_path: Path) -> str:
        """Save PIL canvas image safely to disk with PNG optimization."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(str(file_path), format="PNG", optimize=True)
        return str(file_path)


ticket_generator = TicketGenerator()
