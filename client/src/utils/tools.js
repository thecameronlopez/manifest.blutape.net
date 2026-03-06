const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const FORMAT_DATE = (dateStr) => {
  if (!dateStr) return "";

  // Handle "YYYY-MM-DD" safely (avoid timezone shifting)
  const m = String(dateStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) {
    const year = Number(m[1]);
    const monthIndex = Number(m[2]) - 1; // 0-based
    const day = Number(m[3]);
    return `${MONTHS[monthIndex]} ${day}, ${year}`;
  }

  // Fallback for full datetime strings
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return "";

  const year = d.getFullYear();
  const monthIndex = d.getMonth();
  const day = d.getDate(); // DO NOT +1
  return `${MONTHS[monthIndex]} ${day}, ${year}`;
};

export const FORMAT_PRICE = (cents) => {
  const n = Number(cents);
  if (!Number.isFinite(n)) return "";

  const dollars = n / 100;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(dollars);
};

export const dollarsToCents = (val) => {
  // Accepts: "1234.56", "$1,234.56", "1,234.56"
  const cleaned = String(val).replace(/[^0-9.]/g, "");
  if (!cleaned) return 0;

  const [whole, frac = ""] = cleaned.split(".");
  const frac2 = (frac + "00").slice(0, 2); // exactly 2 digits
  return Number(whole || 0) * 100 + Number(frac2);
};

export const centsToInput = (cents) => {
  return cents === null || cents === undefined || cents === ""
    ? ""
    : FORMAT_PRICE(Number(cents));
};
