-- Media layer: event thumbnails + patron avatars. Event images are real
-- (backfilled from you.com per event title). Patron avatars below are mocked
-- demo people for the leaderboard — app/demo state, not cause data.

alter table events  add column if not exists image_url  text;
alter table patrons add column if not exists avatar_url text;

insert into patrons (name, impact_points, streak_days, avatar_url)
select v.name, v.pts, v.streak, v.av
from (values
  ('Maya Chen',      1840, 21, 'https://randomuser.me/api/portraits/women/44.jpg'),
  ('Diego Ramirez',  1420, 17, 'https://randomuser.me/api/portraits/men/32.jpg'),
  ('Aisha Bello',    1170, 13, 'https://randomuser.me/api/portraits/women/68.jpg'),
  ('Liam O''Connor',  890,  9, 'https://randomuser.me/api/portraits/men/75.jpg'),
  ('Priya Nair',      640,  6, 'https://randomuser.me/api/portraits/women/12.jpg')
) as v(name, pts, streak, av)
where not exists (select 1 from patrons p where p.name = v.name);
