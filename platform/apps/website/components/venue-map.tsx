'use client';

import { useEffect, useRef } from 'react';

/**
 * Small Leaflet map for the venue detail page. Mounts on hydration so the
 * page can stay server-rendered, lazy-loads Leaflet's bundle and CSS.
 *
 * Mirrors scout/web/templates/theatre.html's map block:
 *   - OpenStreetMap tiles
 *   - Square ink marker (Swiss Index style — no rounded blue pin)
 *   - Wheel-zoom off so the map doesn't hijack page scroll
 */
export function VenueMap({
  lat,
  lng,
  name,
}: {
  lat: number;
  lng: number;
  name: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      // Inject Leaflet's stylesheet once per page load. Keeps it out of the
      // critical-path bundle for users who never hit a venue page.
      if (!document.querySelector('link[data-leaflet-css]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        link.setAttribute('data-leaflet-css', 'true');
        document.head.appendChild(link);
      }

      const L = (await import('leaflet')).default;
      if (cancelled || !ref.current) return;

      const map = L.map(ref.current, {
        zoomControl: true,
        scrollWheelZoom: false,
        attributionControl: true,
      }).setView([lat, lng], 15);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);

      const icon = L.divIcon({
        className: 'ts-marker',
        html: '<span class="ts-marker-dot" aria-hidden="true"></span>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });
      L.marker([lat, lng], { icon, title: name }).addTo(map);

      // Aspect-ratio sizing resolves after first paint — recompute so all
      // tiles load.
      requestAnimationFrame(() => map.invalidateSize());
      const onLoad = () => map.invalidateSize();
      window.addEventListener('load', onLoad);

      return () => {
        cancelled = true;
        window.removeEventListener('load', onLoad);
        map.remove();
      };
    })();

    return () => {
      cancelled = true;
    };
  }, [lat, lng, name]);

  return (
    <div
      ref={ref}
      className="show-map"
      style={{ width: '100%', height: '100%', minHeight: 280 }}
    />
  );
}
