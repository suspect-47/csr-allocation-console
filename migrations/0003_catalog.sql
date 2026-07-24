-- Marketplace catalog: real org imagery gathered from you.com, plus a 'listed'
-- status for orgs surfaced from top-charity directories (real, image-rich) that
-- have not been through the full 6-check pipeline. 'cleared' stays the verified
-- tier; 'blocked' the did-not-clear ledger.

alter table causes add column if not exists image_url text;   -- you.com thumbnail
alter table causes add column if not exists logo_url text;     -- you.com favicon
alter table causes add column if not exists blurb text;        -- short description

alter table causes drop constraint if exists causes_status_check;
alter table causes add constraint causes_status_check
    check (status in ('cleared', 'blocked', 'listed'));
