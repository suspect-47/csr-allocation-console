-- News + video gathered from you.com Search for the News tab. Real articles
-- (with imagery) and videos surfaced per pillar; not cause-linked evidence.

create table if not exists news_items (
    id         uuid primary key default gen_random_uuid(),
    kind       text        not null default 'article',   -- article | video
    title      text        not null,
    source     text,
    url        text        not null,
    image_url  text,
    excerpt    text,
    published  text,
    pillar     text,
    video_id   text,
    created_at timestamptz not null default now()
);
create unique index if not exists news_items_url_idx on news_items (url);
