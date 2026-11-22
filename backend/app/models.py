"""OxFood ontology.

Each SQLModel table is an *object type* (Palantir-Foundry style); foreign keys are
the *link types*; POST endpoints in app/routers are the *actions*.
"""
from datetime import date as Date
from pydantic import NaiveDatetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class College(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    short: str
    colour: str = "#002147"
    cost_centre: str = ""


class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str
    name: str
    category: str  # produce, dairy, meat, bakery, dry, fish, frozen
    lead_time_days: int = 1


class CollegeSupplier(SQLModel, table=True):
    """Link: which distributors a college currently buys from."""
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    supplier_id: int = Field(foreign_key="supplier.id", index=True)
    active: bool = True


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    supplier_id: int = Field(foreign_key="supplier.id", index=True)
    sku: str
    name: str
    category: str
    unit: str  # kg, l, each
    pack_size: float  # units per pack
    price: float  # £ per pack
    storage_type: str  # ambient, chilled, frozen
    volume_l: float  # physical space per pack, litres
    shelf_life_days: int
    hazard_class: str = "general"  # raw_meat, raw_fish, ready_to_eat, dairy, produce, allergen_nuts, general
    allergens: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    freezable: bool = False


class StorageUnit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    name: str
    type: str  # fridge, freezer, dry
    capacity_l: float


class Appliance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    name: str
    type: str  # combi_oven, blast_chiller, bratt_pan, fryer, hob, steamer


class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    meal_type: str  # breakfast, lunch, dinner, any
    portion_g: int
    sell_price: float  # normal student price £
    cost_per_portion: float = 0.0
    high_risk: bool = False  # rice / seafood etc
    stages: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    appliances: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    allergens: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    emoji: str = "🍽️"


class RecipeIngredient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipe.id", index=True)
    product_id: int = Field(foreign_key="product.id")
    qty_per_portion: float  # in product.unit


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    created_at: NaiveDatetime
    delivery_date: Date
    status: str = "placed"  # placed, delivered
    exported_at: Optional[NaiveDatetime] = None
    total: float = 0.0


class OrderLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    product_id: int = Field(foreign_key="product.id")
    qty: int  # packs
    unit_price: float


class InventoryLot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    storage_unit_id: Optional[int] = Field(default=None, foreign_key="storageunit.id")
    qty: float  # packs remaining
    received_at: NaiveDatetime
    expiry_date: Date
    status: str = "in_stock"  # in_stock, used, transferred, wasted, listed
    source: str = "order"  # order, transfer
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    transfer_from_college_id: Optional[int] = None


class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    date: Date = Field(index=True)
    meal: str  # breakfast, lunch, dinner
    event_type: str = "informal"  # informal, formal_hall, guest_night, conference, brunch
    booked: int = 0
    attended: int = 0  # ID scans
    staff_on_shift: int = 0
    planned_portions: int = 0
    recipe_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))


class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    pseudo_id: str  # hashed card ID, never the real one
    year: str


class Attendance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="service.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    booked: bool = True
    scanned: bool = False


class WasteEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    service_id: Optional[int] = Field(default=None, foreign_key="service.id")
    recipe_id: Optional[int] = Field(default=None, foreign_key="recipe.id")
    lot_id: Optional[int] = Field(default=None, foreign_key="inventorylot.id")
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    stage: str  # prep_trim, overproduction, servery_leftover, plate_waste, spoilage, cooking_error
    weight_kg: float
    portions_est: int = 0
    value_gbp: float = 0.0
    logged_at: NaiveDatetime
    method: str = "tablet"  # tablet, voice, smart_bin, seed
    disposition: str = "discard"  # discard, compost, chill_reuse, offer_students, marketplace, donate, staff_meal
    note: str = ""


class SurplusListing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    kind: str  # meal_to_students, stock_to_colleges
    recipe_id: Optional[int] = Field(default=None, foreign_key="recipe.id")
    lot_id: Optional[int] = Field(default=None, foreign_key="inventorylot.id")
    waste_event_id: Optional[int] = Field(default=None, foreign_key="wasteevent.id")
    title: str
    qty: float  # portions or packs
    qty_remaining: float
    price: float  # £ per portion / pack
    location: str = "Hall servery"
    created_at: NaiveDatetime
    available_until: NaiveDatetime
    status: str = "open"  # open, sold_out, expired, closed


class Claim(SQLModel, table=True):
    """A student reservation or a college purchase against a listing (records value for future billing)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="surpluslisting.id", index=True)
    buyer_college_id: Optional[int] = Field(default=None, foreign_key="college.id")
    student_pseudo_id: Optional[str] = None
    qty: float
    amount_gbp: float
    pickup_code: str = ""
    created_at: NaiveDatetime


class SupplierIssue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    supplier_id: int = Field(foreign_key="supplier.id", index=True)
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    substitute_product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    date: Date
    type: str  # late, short, damaged, wrong_item, substitution, temp_breach, quality
    notes: str = ""
    resolved: bool = False


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    college_id: int = Field(foreign_key="college.id", index=True)
    audience: str = "students"
    title: str
    body: str
    listing_id: Optional[int] = Field(default=None, foreign_key="surpluslisting.id")
    created_at: NaiveDatetime


class AICall(SQLModel, table=True):
    """Cache + cost ledger for Claude calls."""
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str
    input_hash: str = Field(index=True)
    response_json: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    created_at: NaiveDatetime
