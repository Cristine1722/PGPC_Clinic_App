exports.handler = async (event, context) => {
  // Headers to allow cross-origin requests (CORS) and JSON content
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
  };

  // Handle preflight OPTIONS request
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  try {
    // Robust path parsing: remove /.netlify/functions/api prefix or /api prefix
    let path = event.path.replace(/^(\/\.netlify\/functions\/api|\/api)/, '');
    // Ensure it starts with / and remove trailing slash
    if (!path.startsWith('/')) path = '/' + path;
    path = path.replace(/\/$/, '');
    
    if (event.httpMethod === 'POST') {
      const data = event.body ? JSON.parse(event.body) : {};

      // --- STUDENT & ADMIN LOGIN ---
      if (path === '/login' || path === '/admin-login') {
        const role = path === '/admin-login' ? 'admin' : 'student';
        const isAdmin = role === 'admin';
        
        // Create a mock JWT token
        const payload = JSON.stringify({ username: data.username || "User", is_admin: isAdmin });
        const mockToken = `mockHeader.${Buffer.from(payload).toString('base64')}.mockSignature`;
        
        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ 
            success: true, 
            message: `${role} login successful`, 
            token: mockToken, 
            role: role 
          })
        };
      }

      // --- SIGNUP ---
      if (path === '/signup') {
        const isAdmin = data.is_admin === true;
        const payload = JSON.stringify({ username: data.name || "New User", is_admin: isAdmin });
        const mockToken = `mockHeader.${Buffer.from(payload).toString('base64')}.mockSignature`;

        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ success: true, message: "Account created successfully", token: mockToken })
        };
      }

      // --- FORGOT PASSWORD & RESET ---
      if (path === '/forgot-password' || path === '/reset-password') {
        return { statusCode: 200, headers, body: JSON.stringify({ success: true, reset_token: "123456" }) };
      }

      // --- ADD RECORD ---
      if (path === '/records') {
        return { statusCode: 201, headers, body: JSON.stringify({ success: true, message: "Record saved" }) };
      }
    }

    // --- GET REQUESTS ---
    if (event.httpMethod === 'GET') {
      if (path === '/records' || path === '/my-records') {
        const mockRecords = [
          { id: 1, date: new Date().toISOString(), idnumber: '2023-001', name: 'Sample Student', course: 'BSCS', case: 'Headache', remarks: 'Given Paracetamol' },
          { id: 2, date: new Date().toISOString(), idnumber: '2023-002', name: 'Jane Doe', course: 'BSIT', case: 'Fever', remarks: 'Sent home' }
        ];
        return { statusCode: 200, headers, body: JSON.stringify(mockRecords) };
      }
      
      if (path.match(/^\/records\/\d+$/)) {
        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ id: 1, date: new Date().toISOString(), idnumber: '2023-001', name: 'Sample Student', course: 'BSCS', case: 'Headache', remarks: 'Given Paracetamol' })
        };
      }

      if (path === '/users') {
        return { statusCode: 200, headers, body: JSON.stringify([{ id: 1, idnumber: 'ADMIN01', name: 'Admin User', is_admin: 1 }]) };
      }
    }

    // --- DELETE / PUT ---
    if (event.httpMethod === 'DELETE' || event.httpMethod === 'PUT') {
      return { statusCode: 200, headers, body: JSON.stringify({ success: true, message: "Operation successful (mock)" }) };
    }

    return { statusCode: 404, headers, body: JSON.stringify({ error: "Endpoint not found" }) };

  } catch (error) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: "Server Error: " + error.message }) };
  }
};