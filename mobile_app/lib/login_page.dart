import 'package:flutter/material.dart';
import 'home_page.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController _idController = TextEditingController();
  final TextEditingController _passController = TextEditingController();
  
  // Use the SAME IP as home_page.dart
  final String baseUrl = "http://192.168.101.101:8000"; 
  String? _errorMessage;
  bool _isLoading = false;

  Future<void> _login() async {
    if (_idController.text.isEmpty || _passController.text.isEmpty) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/login'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "id": _idController.text,
          "password": _passController.text,
        }),
      );

      if (response.statusCode == 200) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('emp_id', _idController.text);

        if (!mounted) return;
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => HomePage(empId: _idController.text)),
        );
      } else {
        setState(() {
          _errorMessage = "Invalid Credentials";
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = "Connection Error. Check IP.";
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.security, size: 80, color: Colors.deepPurple),
              const SizedBox(height: 20),
              const Text("Employee Login", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
              const SizedBox(height: 30),
              TextField(
                controller: _idController,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  labelText: 'Employee ID (e.g., EMP001)',
                  prefixIcon: Icon(Icons.person),
                ),
              ),
              const SizedBox(height: 15),
              TextField(
                controller: _passController,
                obscureText: true,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  labelText: 'Password',
                  prefixIcon: Icon(Icons.lock),
                ),
              ),
              if (_errorMessage != null) ...[
                 const SizedBox(height: 15),
                 Text(
                   _errorMessage!,
                   style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                 ),
              ],
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: _isLoading 
                ? const Center(child: CircularProgressIndicator())
                : FilledButton(
                  onPressed: _login,
                  child: const Text("Access System"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
