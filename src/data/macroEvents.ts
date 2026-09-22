import { NewsEvent } from '../types';

export const mockNewsCalendar: NewsEvent[] = [
  {
    id: 'news-1',
    name: 'US Core CPI (MoM / YoY)',
    scheduledTime: Date.now() + 1000 * 60 * 18, // 18 minutes from now
    impact: 'HIGH',
    currency: 'USD',
    quarantineMinutesBefore: 15,
    quarantineMinutesAfter: 20,
    forecast: '0.3%',
    previous: '0.3%',
  },
  {
    id: 'news-2',
    name: 'FOMC Meeting Minutes',
    scheduledTime: Date.now() + 1000 * 60 * 180, // 3 hours
    impact: 'HIGH',
    currency: 'USD',
    quarantineMinutesBefore: 30,
    quarantineMinutesAfter: 30,
  },
  {
    id: 'news-3',
    name: 'Initial Jobless Claims',
    scheduledTime: Date.now() - 1000 * 60 * 120, // 2 hours ago
    impact: 'HIGH',
    currency: 'USD',
    quarantineMinutesBefore: 15,
    quarantineMinutesAfter: 15,
    actual: '215K',
    forecast: '220K',
    previous: '228K',
  },
  {
    id: 'news-4',
    name: 'ISM Manufacturing PMI',
    scheduledTime: Date.now() + 1000 * 60 * 360,
    impact: 'HIGH',
    currency: 'USD',
    quarantineMinutesBefore: 15,
    quarantineMinutesAfter: 20,
    forecast: '49.8',
    previous: '48.9',
  }
];
