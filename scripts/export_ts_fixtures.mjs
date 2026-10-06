// Exports the web store's catalog and parity fixtures by running the web repo's own TypeScript
// (src/data/products.ts, src/lib/pricing.ts, server/orders.ts). Needs Node >= 22.18 (type stripping).
//
//   WEB_REPO=../bernice_hairplace_web node scripts/export_ts_fixtures.mjs
//
// Writes:
//   app/catalog/products.json            the catalog the API serves (catalog stays in code for v1, ADR 0002)
//   tests/fixtures/parity_pricing.json   unit price / delivery fee / total cases
//   tests/fixtures/parity_checkout.json  checkout validation accept/reject cases
import { register } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const webRepo = resolve(root, process.env.WEB_REPO ?? '../bernice_hairplace_web');

// The web server code imports './x.js' for files that are really './x.ts'.
register(
  'data:text/javascript,' +
    encodeURIComponent(`
      export async function resolve(specifier, context, next) {
        try { return await next(specifier, context); }
        catch (err) {
          if (err?.code === 'ERR_MODULE_NOT_FOUND' && specifier.endsWith('.js')) {
            return next(specifier.slice(0, -3) + '.ts', context);
          }
          throw err;
        }
      }`),
  import.meta.url
);

const load = (path) => import(pathToFileURL(resolve(webRepo, path)).href);
const { PRODUCTS } = await load('src/data/products.ts');
const { getUnitPrice, computeDeliveryFee } = await load('src/lib/pricing.ts');
const { parseCheckoutInput, createPendingOrder, OrderInputError } = await load('server/orders.ts');

// A Supabase stand-in that accepts every write, so createPendingOrder runs its real pricing/validation.
const fakeSupabase = {
  from: () => {
    const chain = {
      insert: () => chain,
      update: () => chain,
      delete: () => chain,
      eq: () => chain,
      select: () => chain,
      single: async () => ({ data: { id: 'order-id' }, error: null }),
      then: (ok) => ok({ data: null, error: null }),
    };
    return chain;
  },
};
const user = { id: '00000000-0000-0000-0000-000000000001' };

const runCheckout = async (body) => {
  try {
    const input = parseCheckoutInput(body);
    const order = await createPendingOrder(fakeSupabase, user, input);
    return {
      ok: true,
      fulfillment_method: input.fulfillmentMethod,
      address: input.address,
      subtotal: order.subtotal,
      delivery_fee: order.deliveryFee,
      total: order.total,
      lines: order.lines.map((l) => ({
        product_id: l.product_id,
        selected_length: l.selected_length,
        quantity: l.quantity,
        unit_price: l.unit_price,
        line_total: l.line_total,
      })),
    };
  } catch (err) {
    if (err instanceof OrderInputError) return { ok: false, error: err.message };
    throw err;
  }
};

// Deterministic PRNG so fixtures are stable between runs.
let seed = 20261006;
const rand = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const pick = (xs) => xs[Math.floor(rand() * xs.length)];

// ───────────── pricing ─────────────
const methods = ['courier_express', 'studio_pickup'];
const unitPrices = [];
for (const p of PRODUCTS) {
  for (let length = 0; length <= 60; length++) {
    unitPrices.push({ product_id: p.id, length, unit_price: getUnitPrice(p, length) });
  }
  for (const length of p.lengths) {
    unitPrices.push({ product_id: p.id, length, unit_price: getUnitPrice(p, length) });
  }
}

const deliveryFees = [];
for (const subtotal of [0, 1, 4500, 149_999, 150_000, 150_001, 999_999]) {
  for (const method of methods) deliveryFees.push({ subtotal, method, fee: computeDeliveryFee(subtotal, method) });
}

const address = {
  firstName: 'Ada',
  lastName: 'Okafor',
  email: 'ada@example.com',
  phone: '+234 801 234 5678',
  streetAddress: '12 Admiralty Way',
  district: 'Lekki Phase 1',
};

const baskets = [];
for (const p of PRODUCTS) {
  for (const length of p.lengths) {
    for (const method of methods) {
      for (const quantity of [1, 2]) {
        const items = [{ productId: p.id, selectedLength: length, quantity }];
        baskets.push({ fulfillment_method: method, items, expected: await runCheckout({ fulfillmentMethod: method, address, items }) });
      }
    }
  }
}
for (let i = 0; i < 60; i++) {
  const items = [];
  const n = 1 + Math.floor(rand() * 5);
  for (let j = 0; j < n; j++) {
    const p = pick(PRODUCTS);
    items.push({ productId: p.id, selectedLength: pick(p.lengths), quantity: 1 + Math.floor(rand() * 20) });
  }
  const method = pick(methods);
  baskets.push({ fulfillment_method: method, items, expected: await runCheckout({ fulfillmentMethod: method, address, items }) });
}

// ───────────── checkout validation ─────────────
const p0 = PRODUCTS[0];
const item = { productId: p0.id, selectedLength: p0.lengths[0], quantity: 1 };
const base = { fulfillmentMethod: 'courier_express', address, items: [item] };
const withAddress = (patch) => ({ ...base, address: { ...address, ...patch } });

const cases = [
  ['valid courier order', base],
  ['valid pickup order without street', { ...base, fulfillmentMethod: 'studio_pickup', address: { ...address, streetAddress: '' } }],
  ['unknown fulfilment defaults to courier', { ...base, fulfillmentMethod: 'drone' }],
  ['missing fulfilment defaults to courier', { address, items: [item] }],
  ['missing first name', withAddress({ firstName: '' })],
  ['whitespace last name', withAddress({ lastName: '   ' })],
  ['missing address object', { ...base, address: undefined }],
  ['invalid email', withAddress({ email: 'ada@example' })],
  ['email with spaces', withAddress({ email: 'ada @example.com' })],
  ['email padded with spaces is trimmed', withAddress({ email: '  ada@example.com  ' })],
  ['phone too short', withAddress({ phone: '12-34-5' })],
  ['phone exactly 7 digits', withAddress({ phone: '(123) 4567' })],
  ['courier without street', withAddress({ streetAddress: ' ' })],
  ['state and country are forced', withAddress({ state: 'Abuja', country: 'Ghana' })],
  ['long fields are truncated', withAddress({ firstName: 'A'.repeat(120), deliveryNotes: 'n'.repeat(900), streetAddress: 's'.repeat(300) })],
  ['numeric phone value is stringified', withAddress({ phone: 8012345678 })],
  ['empty bag', { ...base, items: [] }],
  ['items not a list', { ...base, items: 'nope' }],
  ['missing items', { fulfillmentMethod: 'courier_express', address }],
  ['51 lines', { ...base, items: Array.from({ length: 51 }, () => item) }],
  ['50 lines', { ...base, items: Array.from({ length: 50 }, () => item) }],
  ['unknown product', { ...base, items: [{ ...item, productId: 'prod-nope' }] }],
  ['quantity 0', { ...base, items: [{ ...item, quantity: 0 }] }],
  ['quantity 21', { ...base, items: [{ ...item, quantity: 21 }] }],
  ['quantity 20', { ...base, items: [{ ...item, quantity: 20 }] }],
  ['fractional quantity', { ...base, items: [{ ...item, quantity: 1.5 }] }],
  ['quantity as numeric string', { ...base, items: [{ ...item, quantity: '2' }] }],
  ['invalid length', { ...base, items: [{ ...item, selectedLength: 19 }] }],
  ['length as numeric string', { ...base, items: [{ ...item, selectedLength: String(p0.lengths[1]) }] }],
  ['bad quantity is reported before a later unknown product', { ...base, items: [{ ...item, quantity: 0 }, { ...item, productId: 'x' }] }],
  ['free delivery threshold reached', { ...base, items: [{ productId: p0.id, selectedLength: p0.defaultLength, quantity: 1 }] }],
  ['below free delivery threshold', { ...base, items: [{ productId: PRODUCTS[1].id, selectedLength: PRODUCTS[1].defaultLength, quantity: 1 }] }],
];

const checkout = [];
for (const [name, body] of cases) checkout.push({ name, body, out_of_stock: [], expected: await runCheckout(body) });

// Out-of-stock: flip a product temporarily (the API reads the same flag from its catalog).
const oos = PRODUCTS[2];
oos.isInStock = false;
const oosBody = { ...base, items: [item, { productId: oos.id, selectedLength: oos.lengths[0], quantity: 1 }] };
checkout.push({ name: 'out-of-stock item', body: oosBody, out_of_stock: [oos.id], expected: await runCheckout(oosBody) });
oos.isInStock = true;

// ───────────── write ─────────────
const write = (path, data) => {
  const full = resolve(root, path);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, JSON.stringify(data, null, 2) + '\n');
  console.log(`wrote ${path}`);
};

const catalogJson = JSON.stringify(PRODUCTS);
const catalogSha256 = createHash('sha256').update(catalogJson).digest('hex');
write('app/catalog/products.json', PRODUCTS);
write('tests/fixtures/parity_pricing.json', { catalog_sha256: catalogSha256, unit_prices: unitPrices, delivery_fees: deliveryFees, baskets });
write('tests/fixtures/parity_checkout.json', { catalog_sha256: catalogSha256, cases: checkout });
