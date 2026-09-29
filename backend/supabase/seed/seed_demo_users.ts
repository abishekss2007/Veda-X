/**
 * AyurCTMS Demo User Seeder
 * Creates the 9 demo accounts in Supabase Auth and approves their profiles.
 * STRICTLY FOR DEMONSTRATION & LOCAL DEVELOPMENT ONLY.
 */

import { getServerClient } from '../client';

export const DEMO_USERS = [
  {
    role: 'Admin',
    email: 'admin@ayurctms.demo',
    password: 'Admin@Demo#2026',
    fullName: 'System Administrator',
    site: 'SITE-HQ'
  },
  {
    role: 'Principal Investigator',
    email: 'pi@ayurctms.demo',
    password: 'Pi@Demo#2026',
    fullName: 'Prof. (Dr.) Rajeshwar Sharma',
    site: 'SITE-01'
  },
  {
    role: 'Research Coordinator',
    email: 'coordinator@ayurctms.demo',
    password: 'Coord@Demo#2026',
    fullName: 'Dr. Sunita Patel, BAMS',
    site: 'SITE-01'
  },
  {
    role: 'Doctor / Investigator',
    email: 'doctor@ayurctms.demo',
    password: 'Doctor@Demo#2026',
    fullName: 'Dr. Arvind Joshi, MD (Ayu)',
    site: 'SITE-01'
  },
  {
    role: 'Monitor',
    email: 'monitor@ayurctms.demo',
    password: 'Monitor@Demo#2026',
    fullName: 'Vikram Verma, CRA',
    site: 'SITE-01'
  },
  {
    role: 'EC Member',
    email: 'ec@ayurctms.demo',
    password: 'Ethics@Demo#2026',
    fullName: 'Justice (Retd.) M. K. Narayanan',
    site: 'EC-BOARD'
  },
  {
    role: 'PV Officer',
    email: 'pv@ayurctms.demo',
    password: 'Pharma@Demo#2026',
    fullName: 'Dr. Gayatri Devi, MD (Ayu)',
    site: 'SITE-01'
  },
  {
    role: 'Auditor / Regulator',
    email: 'auditor@ayurctms.demo',
    password: 'Audit@Demo#2026',
    fullName: 'K. R. Sengupta, ISO Lead Auditor',
    site: 'SITE-HQ'
  },
  {
    role: 'Institution Leadership',
    email: 'leader@ayurctms.demo',
    password: 'Leader@Demo#2026',
    fullName: 'Prof. (Dr.) Tanuja Nesari, Director',
    site: 'SITE-HQ'
  }
];

export async function seedDemoUsers() {
  console.log('[AyurCTMS] Seeding 9 statutory demo accounts into Supabase Auth...');
  const supabase = getServerClient();

  for (const user of DEMO_USERS) {
    try {
      // 1. Create or retrieve auth user via Supabase Admin API
      const { data: authData, error: authError } = await supabase.auth.admin.createUser({
        email: user.email,
        password: user.password,
        email_confirm: true,
        user_metadata: {
          full_name: user.fullName,
          role: user.role,
          site: user.site,
          notice_version: 'DPDP-V1.0'
        }
      });

      if (authError) {
        if (authError.message.includes('already been registered')) {
          console.log(`[Seed] User ${user.email} already exists.`);
        } else {
          console.error(`[Seed Error] Failed to create ${user.email}:`, authError.message);
          continue;
        }
      }

      // 2. Ensure profile is set to 'approved' for demo access
      const userId = authData?.user?.id;
      if (userId) {
        await supabase
          .from('profiles')
          .update({
            status: 'approved',
            role: user.role,
            site: user.site,
            full_name: user.fullName
          })
          .eq('id', userId);
      }

      console.log(`[Seed Success] ${user.role} (${user.email}) ready.`);
    } catch (err: any) {
      console.error(`[Seed Exception] ${user.email}:`, err.message);
    }
  }

  console.log('[AyurCTMS] Demo user seeding completed successfully.');
}
