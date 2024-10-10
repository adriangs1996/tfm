
import express, { Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import bodyParser from 'body-parser';

const app = express();
app.use(bodyParser.json());

// Simple in-memory store for this example
const users: { [key: string]: string } = {};

app.post('/register', async (req: Request, res: Response) => {
    const { username, password } = req.body;

    // Hash the password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Store user
    users[username] = hashedPassword;

    res.status(201).json({ message: 'User registered successfully' });
});

app.post('/login', async (req: Request, res: Response) => {
    const { username, password } = req.body;

    const storedPasswordHash = users[username];
    if (!storedPasswordHash) {
        return res.status(401).json({ message: 'Invalid username or password' });
    }

    // Compare the password with the stored hash
    const match = await bcrypt.compare(password, storedPasswordHash);

    if (match) {
        res.status(200).json({ message: 'Login successful' });
    } else {
        res.status(401).json({ message: 'Invalid username or password' });
    }
});

app.listen(3000, () => {
    console.log('Server is running on http://localhost:3000');
});
