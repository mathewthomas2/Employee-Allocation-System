import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:vibration/vibration.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'config.dart';

class HomePage extends StatefulWidget {
  final String empId;
  const HomePage({super.key, required this.empId});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String status = "Monitoring Zone...";
  String? activeAlert;
  String? activeZoneId;
  bool isClaimed = false;
  Timer? _timer;

  // Use the connection string from config.dart
  final String baseUrl = Config.baseUrl; 

  @override
  void initState() {
    super.initState();
    _checkNotifications(); // Fetch immediately on App Load
    _startPolling();
  }

  @override
  void dispose() {
    _timer?.cancel();
    Vibration.cancel(); // Stop vibration if user leaves app
    super.dispose();
  }

  void _startPolling() {
    _timer = Timer.periodic(const Duration(seconds: 2), (timer) {
      _checkNotifications();
    });
  }

  Future<void> _checkNotifications() async {
    try {
      // 1. Check Personal Notifications
      final response = await http.get(Uri.parse('$baseUrl/notifications/${widget.empId}'));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['has_notification'] == true) {
           bool newIsClaimed = data['is_claimed'] ?? false;
           
           // Trigger Sound & Vibration (If it's a NEW alert, OR if a claimed alert was just Revoked)
           if (activeAlert == null || (isClaimed && !newIsClaimed)) {
              // Pattern: [Wait 500ms, Buzz 500ms] repeated
              Vibration.vibrate(pattern: [500, 500], repeat: 0); 
           }

           setState(() {
             activeAlert = data['message'];
             activeZoneId = data['zone_id'];
             isClaimed = newIsClaimed;
             status = isClaimed ? "Heading to Zone!" : "Action Required!";
           });
           // _showAlertDialog(data['message']); // relying on UI button below
        } else {
           if (activeAlert == null) {
             setState(() {
               status = "Monitoring Zone...";
             });
           }
        }
      }
    } catch (e) {
      setState(() {
        status = "Connection Error (Check IP)";
      });
      print(e);
    }
  }

  void _showAlertDialog(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("ALERT: $message"),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 5),
        action: SnackBarAction(label: "ACKNOWLEDGE", textColor: Colors.white, onPressed: () {
           Vibration.cancel();
           setState(() {
             activeAlert = null;
             status = "Monitoring Zone...";
           });
        }),
      ),
    );
  }

  Future<void> _claimAlert() async {
    if (activeZoneId == null) return;
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/claim_alert'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'employee_id': widget.empId,
          'zone_id': activeZoneId
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
           Vibration.cancel();
           setState(() {
             isClaimed = true;
             status = "Heading to Zone!";
           });
           ScaffoldMessenger.of(context).showSnackBar(
             const SnackBar(content: Text("Alert Claimed! Proceed to Zone.")),
           );
        } else {
           ScaffoldMessenger.of(context).showSnackBar(
             SnackBar(content: Text(data['message'])),
           );
        }
      }
    } catch (e) {
      print("Failed to claim: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    bool isAlert = activeAlert != null;

    return Scaffold(
      appBar: AppBar(
        title: Text("Employee: ${widget.empId}"),
        backgroundColor: isAlert ? Colors.red : Colors.deepPurple[100],
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
               // Logout Logic
               final prefs = await SharedPreferences.getInstance();
               await prefs.clear(); // Clear Session
               
               if (!mounted) return;
               // Navigate back to Login and remove all history
               Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
            },
          )
        ],
      ),
      backgroundColor: isAlert ? Colors.red[50] : Colors.white,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isAlert ? Icons.warning_amber_rounded : Icons.check_circle_outline,
              size: 100,
              color: isAlert ? Colors.red : Colors.green,
            ),
            const SizedBox(height: 20),
            Text(
              status,
              style: TextStyle(
                fontSize: 24, 
                fontWeight: FontWeight.bold,
                color: isAlert ? Colors.red : Colors.black87
              ),
              textAlign: TextAlign.center,
            ),
            if (activeAlert != null) ...[
               const SizedBox(height: 20),
               Container(
                 padding: const EdgeInsets.all(16),
                 margin: const EdgeInsets.symmetric(horizontal: 20),
                 decoration: BoxDecoration(
                   color: Colors.red[100],
                   borderRadius: BorderRadius.circular(10),
                   border: Border.all(color: Colors.red)
                 ),
                 child: Text(
                   activeAlert!,
                   style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                   textAlign: TextAlign.center,
                 ),
               ),
               const SizedBox(height: 30),
               // Alert Action Buttons
               if (!isClaimed) 
                 ElevatedButton.icon(
                   onPressed: () {
                     Vibration.cancel();
                     _claimAlert(); 
                   },
                   icon: const Icon(Icons.front_hand),
                   label: const Text("I'm On It! (Claim)"),
                   style: ElevatedButton.styleFrom(
                     backgroundColor: Colors.blueAccent,
                     foregroundColor: Colors.white,
                     padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                   ),
                 )
               else
                 Container(
                   padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                   decoration: BoxDecoration(
                     color: Colors.green,
                     borderRadius: BorderRadius.circular(30)
                   ),
                   child: Row(
                     mainAxisSize: MainAxisSize.min,
                     children: const [
                       Icon(Icons.directions_run, color: Colors.white),
                       SizedBox(width: 10),
                       Text("Claimed - Proceeding...", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold))
                     ]
                   )
                 )
            ]
          ],
        ),
      ),
    );
  }
}
