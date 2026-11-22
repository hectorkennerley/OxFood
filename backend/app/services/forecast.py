"""Covers forecast: booked × historical show-up rate for similar services × event buffer."""
from datetime import date, timedelta

from sqlmodel import Session, select

from app.models import Service

# Formal/guest nights are plated at a fixed time, so cook close to the forecast.
# Informal cafeteria service is flexible, so it gets a slightly larger safety margin.
BUFFER = {"formal_hall": 0.02, "guest_night": 0.02, "informal": 0.05, "brunch": 0.06, "conference": 0.03}


def show_rate(session: Session, college_id: int, meal: str, weekday: int, event_type: str,
              before: date, weeks: int = 6) -> tuple[float, int]:
    """Show-up rate from past services of the same kind. Returns (rate, sample size)."""
    rows = session.exec(
        select(Service).where(Service.college_id == college_id, Service.meal == meal,
                              Service.date < before, Service.date >= before - timedelta(weeks=weeks), Service.booked > 0)
    ).all()
    same = [r for r in rows if r.event_type == event_type and (event_type != "informal" or r.date.weekday() == weekday)]
    if len(same) < 2:
        same = [r for r in rows if r.event_type == event_type] or rows
    if not same:
        return 0.8, 0
    booked = sum(r.booked for r in same)
    attended = sum(r.attended for r in same)
    return (attended / booked if booked else 0.8), len(same)


def forecast_service(session: Session, svc: Service) -> dict:
    rate, n = show_rate(session, svc.college_id, svc.meal, svc.date.weekday(), svc.event_type, svc.date)
    buf = BUFFER.get(svc.event_type, 0.05)
    expected = round(svc.booked * rate)
    recommended = round(expected * (1 + buf))
    naive = round(svc.booked * 1.05)  # what kitchens typically do: cook for everyone booked + 5%
    return {
        "service_id": svc.id,
        "date": svc.date.isoformat(),
        "meal": svc.meal,
        "event_type": svc.event_type,
        "booked": svc.booked,
        "show_rate": round(rate, 3),
        "sample_size": n,
        "expected_covers": expected,
        "buffer_pct": round(buf * 100),
        "recommended_portions": recommended,
        "naive_portions": naive,
        "portions_saved": max(0, naive - recommended),
        "staff_on_shift": svc.staff_on_shift,
        "explanation": (f"{svc.booked} booked. Past {_label(svc)} services showed {rate:.0%} of bookings "
                        f"({n} services), so expect {expected}. Cook {recommended} (+{buf:.0%} buffer)."),
    }


def _label(svc: Service) -> str:
    if svc.event_type != "informal":
        return svc.event_type.replace("_", " ")
    return f"{svc.date.strftime('%A')} {svc.meal}"
