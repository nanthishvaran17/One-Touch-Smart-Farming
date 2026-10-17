from datetime import datetime, timezone
from backend.app.db.session import engine, Base, SessionLocal
from backend.app.models.entities import (
    User, Farm, Device, Motor, MotorSafetyConfig, MotorPipeline,
    Schedule, Notification
)
from backend.app.core.security import hash_password

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if initial farmer user exists
        farmer = db.query(User).filter(User.phone_number == "9876543210").first()
        if not farmer:
            farmer = User(
                phone_number="9876543210",
                full_name="Murugan Farmer (முருகன்)",
                hashed_password=hash_password("FarmerPass123!"),
                preferred_language="ta",
                role="farmer",
                ui_mode="easy"
            )
            db.add(farmer)
            db.flush()

            # Create default farm
            farm = Farm(
                owner_id=farmer.id,
                name="Green Acres Farm (பசுமை தோட்டம்)",
                location="Pollachi, Tamil Nadu",
                latitude=10.6609,
                longitude=77.0048,
                timezone="Asia/Kolkata",
                acreage=8.5
            )
            db.add(farm)
            db.flush()

            # Create registered hardware controller device
            device = Device(
                serial_number="FS-CTRL-88219",
                pairing_token_hash=hash_password("PAIR-88219"),
                device_name="Palar River Main Controller",
                is_paired=True,
                farm_id=farm.id,
                ip_address="192.168.1.105",
                firmware_version="v2.4.0-prod",
                status="ONLINE",
                last_heartbeat=datetime.now(timezone.utc)
            )
            db.add(device)
            db.flush()

            # Create Motor 1: Borewell Motor
            borewell_motor = Motor(
                farm_id=farm.id,
                device_id=device.id,
                name="Borewell Motor (போர்வெல் மோட்டார்)",
                motor_type="submersible",
                hp_rating=7.5,
                relay_channel=1,
                status="STOPPED",
                total_runtime_hours=142.5
            )
            db.add(borewell_motor)
            db.flush()

            # Safety configuration for 7.5 HP motor
            safety = MotorSafetyConfig(
                motor_id=borewell_motor.id,
                min_voltage=180.0,
                max_voltage=265.0,
                max_current=22.5,
                dry_run_current=7.0,
                max_runtime_minutes=360,
                star_delta_delay_seconds=6,
                dry_run_trip_delay_seconds=15
            )
            db.add(safety)

            # Seven-Pipeline Mechanical Product Setup (5 rotations each!)
            pipeline_names = [
                ("North Paddy Field (வடக்கு நெல் வயல்)", 1),
                ("East Coconut Grove (கிழக்கு தென்னந்தோப்பு)", 2),
                ("South Banana Plot (தெற்கு வாழை தோட்டம்)", 3),
                ("West Vegetable Patch (மேற்கு காய்கறி தோட்டம்)", 4),
                ("Central Drip Zone (மத்திய சொட்டு நீர் பகுதி)", 5),
                ("Nursery & Seedling Bed (நாற்றுப்பண்ணை)", 6),
                ("Orchard & Drip Line 7 (பழத்தோட்டம் வரிசை 7)", 7),
            ]
            for name, idx in pipeline_names:
                pipeline = MotorPipeline(
                    motor_id=borewell_motor.id,
                    pipeline_index=idx,
                    name=name,
                    target_rotations=5,  # 5 rotations requirement
                    actual_rotations=0,
                    is_enabled=True,
                    status="IDLE" if idx > 1 else "FLOWING",
                    flow_rate_lpm=45.0 if idx == 1 else 0.0,
                    last_verified_position=idx
                )
                db.add(pipeline)

            # Create Motor 2: Field Drip Motor
            field_motor = Motor(
                farm_id=farm.id,
                device_id=device.id,
                name="Canal Lift Motor (வாய்க்கால் மோட்டார்)",
                motor_type="monoblock",
                hp_rating=5.0,
                relay_channel=2,
                status="STOPPED",
                total_runtime_hours=88.0
            )
            db.add(field_motor)
            db.flush()

            field_safety = MotorSafetyConfig(
                motor_id=field_motor.id,
                min_voltage=190.0,
                max_voltage=260.0,
                max_current=16.0,
                dry_run_current=5.5,
                max_runtime_minutes=240
            )
            db.add(field_safety)

            # Setup 7 pipelines for field motor as well
            for idx in range(1, 8):
                db.add(MotorPipeline(
                    motor_id=field_motor.id,
                    pipeline_index=idx,
                    name=f"Canal Pipeline Line {idx}",
                    target_rotations=5,
                    actual_rotations=0,
                    is_enabled=True,
                    status="IDLE",
                    last_verified_position=idx
                ))

            # Add default Daily Irrigation Schedule
            schedule = Schedule(
                motor_id=borewell_motor.id,
                farm_id=farm.id,
                name="Morning Paddy Irrigation (காலை பாசனம்)",
                schedule_type="DAILY",
                days_of_week="mon,tue,wed,thu,fri,sat,sun",
                start_time="06:00",
                stop_time="07:30",
                duration_minutes=90,
                pipeline_mode="ALL_7_SEQUENTIAL",
                pipeline_sequence=[1, 2, 3, 4, 5, 6, 7],
                is_active=True,
                timezone="Asia/Kolkata"
            )
            db.add(schedule)

            # Add initial welcome notification
            notif = Notification(
                user_id=farmer.id,
                farm_id=farm.id,
                motor_id=borewell_motor.id,
                category="SYSTEM",
                title_en="Welcome to Farm Saathi",
                title_ta="பார்ம் சாத்திக்கு நல்வரவு",
                message_en="Your Smart Controller FS-CTRL-88219 and 7-Pipeline Irrigation System are ready for safe automation.",
                message_ta="உங்கள் ஸ்மார்ட் கன்ட்ரோலர் FS-CTRL-88219 மற்றும் 7-பைப்லைன் பாசன அமைப்பு தயார் நிலையில் உள்ளது.",
                severity="INFO"
            )
            db.add(notif)
            db.commit()
            print("Database initialized with seed data successfully!")
        else:
            print("Database already contains data.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
