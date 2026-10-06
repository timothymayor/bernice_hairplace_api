-- Bernice Hairplace — initial schema.
-- Run once in Supabase → SQL Editor (or `supabase db push`).
-- The product catalog lives in code (src/data/products.ts); product_id columns store its ids.

-- ───────────────────────── helpers ─────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ───────────────────────── profiles ─────────────────────────
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null,
  full_name text,
  avatar_url text,
  phone text,
  default_address jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Create a profile automatically when someone signs in with Google for the first time.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;

create policy "Profiles: read own" on public.profiles
  for select to authenticated using ((select auth.uid()) = id);
create policy "Profiles: update own" on public.profiles
  for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

-- ───────────────────────── orders ─────────────────────────
-- Orders are created and updated only by the server (service role) in /api.
create table public.orders (
  id uuid primary key default gen_random_uuid(),
  order_number text not null unique,
  user_id uuid not null references auth.users (id) on delete restrict,
  customer_name text not null,
  customer_email text not null,
  customer_phone text not null,
  shipping_address jsonb not null,
  fulfillment_method text not null check (fulfillment_method in ('courier_express', 'studio_pickup')),
  subtotal integer not null check (subtotal >= 0),
  delivery_fee integer not null check (delivery_fee >= 0),
  total integer not null check (total = subtotal + delivery_fee),
  currency text not null default 'NGN' check (currency = 'NGN'),
  status text not null default 'pending_payment' check (
    status in ('pending_payment', 'paid', 'processing', 'in_transit', 'delivered',
               'payment_failed', 'payment_reversed', 'cancelled')
  ),
  payment_status text not null default 'initialized' check (
    payment_status in ('initialized', 'pending', 'success', 'failed', 'reversed')
  ),
  payment_reference text not null unique,
  payment_channel text,
  paystack_transaction_id text,
  paid_at timestamptz,
  waybill_number text,
  confirmation_email_sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index orders_user_id_created_at_idx on public.orders (user_id, created_at desc);

create trigger orders_set_updated_at
  before update on public.orders
  for each row execute function public.set_updated_at();

create table public.order_items (
  id bigint generated always as identity primary key,
  order_id uuid not null references public.orders (id) on delete cascade,
  product_id text not null,
  product_name text not null,
  sku text not null,
  category_label text not null default '',
  image text not null default '',
  selected_length integer not null check (selected_length > 0),
  quantity integer not null check (quantity > 0),
  unit_price integer not null check (unit_price >= 0),
  line_total integer not null check (line_total = unit_price * quantity)
);

create index order_items_order_id_idx on public.order_items (order_id);

alter table public.orders enable row level security;
alter table public.order_items enable row level security;

create policy "Orders: read own" on public.orders
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Order items: read own" on public.order_items
  for select to authenticated using (
    exists (select 1 from public.orders o where o.id = order_id and o.user_id = (select auth.uid()))
  );

-- ───────────────────────── bag & wishlist ─────────────────────────
create table public.cart_items (
  user_id uuid not null references auth.users (id) on delete cascade,
  product_id text not null,
  selected_length integer not null check (selected_length > 0),
  quantity integer not null check (quantity between 1 and 20),
  updated_at timestamptz not null default now(),
  primary key (user_id, product_id, selected_length)
);

alter table public.cart_items enable row level security;

create policy "Cart: read own" on public.cart_items
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Cart: insert own" on public.cart_items
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Cart: update own" on public.cart_items
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Cart: delete own" on public.cart_items
  for delete to authenticated using ((select auth.uid()) = user_id);

-- Atomically replaces the signed-in customer's bag (runs with the caller's permissions, so RLS applies).
create or replace function public.replace_cart(items jsonb)
returns void language sql security invoker set search_path = '' as $$
  delete from public.cart_items where user_id = (select auth.uid());
  insert into public.cart_items (user_id, product_id, selected_length, quantity)
  select (select auth.uid()), x.product_id, x.selected_length, x.quantity
  from jsonb_to_recordset(coalesce(items, '[]'::jsonb)) as x(product_id text, selected_length integer, quantity integer);
$$;

revoke execute on function public.replace_cart(jsonb) from public, anon;
grant execute on function public.replace_cart(jsonb) to authenticated;

create table public.wishlist_items (
  user_id uuid not null references auth.users (id) on delete cascade,
  product_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, product_id)
);

alter table public.wishlist_items enable row level security;

create policy "Wishlist: read own" on public.wishlist_items
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Wishlist: insert own" on public.wishlist_items
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Wishlist: delete own" on public.wishlist_items
  for delete to authenticated using ((select auth.uid()) = user_id);

-- ───────────────────────── requests & newsletter ─────────────────────────
create table public.custom_wig_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null default auth.uid(),
  cap_size text not null,
  lace_type text not null,
  texture text not null,
  density text not null,
  parting text not null,
  status text not null default 'new' check (status in ('new', 'contacted', 'in_progress', 'completed', 'declined')),
  created_at timestamptz not null default now()
);

alter table public.custom_wig_requests enable row level security;

create policy "Custom wig requests: anyone can submit" on public.custom_wig_requests
  for insert to anon, authenticated
  with check (user_id is null or user_id = (select auth.uid()));
create policy "Custom wig requests: read own" on public.custom_wig_requests
  for select to authenticated using ((select auth.uid()) = user_id);

create table public.newsletter_subscribers (
  id bigint generated always as identity primary key,
  email text not null unique check (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$' and length(email) <= 254),
  created_at timestamptz not null default now()
);

alter table public.newsletter_subscribers enable row level security;

create policy "Newsletter: anyone can subscribe" on public.newsletter_subscribers
  for insert to anon, authenticated with check (true);
