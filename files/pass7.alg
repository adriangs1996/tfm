
import { Injectable } from '@nestjs/common';
import * as bcrypt from 'bcryptjs';

import { Controller, Post, Body, HttpException, HttpStatus } from '@nestjs/common';
import { AuthService } from './auth.service';

@Controller('auth')
export class AuthController {
    constructor(private readonly authService: AuthService) {}

    @Post('register')
    async register(@Body('username') username: string, @Body('password') password: string) {
        await this.authService.register(username, password);
        return { message: 'User registered successfully' };
    }

    @Post('login')
    async login(@Body('username') username: string, @Body('password') password: string) {
        const isValid = await this.authService.validateUser(username, password);
        if (!isValid) {
            throw new HttpException('Invalid username or password', HttpStatus.UNAUTHORIZED);
        }
        return { message: 'Login successful' };
    }
}

@Injectable()
export class AuthService {
    private readonly users: { [key: string]: string } = {};

    async register(username: string, password: string): Promise<void> {
        const hashedPassword = await bcrypt.hash(password, 10);
        this.users[username] = hashedPassword;
    }

    async validateUser(username: string, password: string): Promise<boolean> {
        const storedPasswordHash = this.users[username];
        if (!storedPasswordHash) {
            return false;
        }
        return await bcrypt.compare(password, storedPasswordHash);
    }
}
