import { prisma } from '@/lib/prisma';
export async function GET(req) {
  try {
    const users = await prisma.user.findMany();
    return new Response(JSON.stringify(users), { status: 200 });
  } catch (error) {
    console.error('Database error:', error);
    return new Response(
      JSON.stringify({ error: 'Database connection failed' }),
      { status: 500 }
    );
  }
}

// export async function POST(req) {
//   try {
//     const body = await req.json();
//     const user = await prisma.user.create({
//       data: {
//         email: body.email,
//         passwordHash: body.passwordHash,
//         name: body.name,
//       },
//     });
//     return new Response(JSON.stringify(user), { status: 201 });
//   } catch (error) {
//     console.error('Database error:', error);
//     return new Response(JSON.stringify({ error: 'Failed to create user' }), { status: 500 });
//   }
// }

// import { prisma } from '@/lib/prisma';

// export async function GET(req) {
//   try {
//     const users = await prisma.user.findMany();
//     return new Response(JSON.stringify(users), { status: 200 });
//   } catch (error) {
//     console.error('Database error:', error);
//     return new Response(JSON.stringify({ error: 'Database connection failed' }), { status: 500 });
//   }
// }
