<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AION Conscious Engine - Holodeck Cube View</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: radial-gradient(circle at 30% 20%, #0a0a2e 0%, #000012 100%);
            overflow: hidden;
            font-family: 'Courier New', monospace;
            color: #00ffff;
        }

        .container {
            width: 100vw;
            height: 100vh;
            position: relative;
            perspective: 1000px;
        }

        .cube-container {
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%) rotateX(15deg) rotateY(25deg);
            width: 400px;
            height: 400px;
            transform-style: preserve-3d;
            animation: floatCube 6s ease-in-out infinite;
        }

        .cube {
            width: 100%;
            height: 100%;
            position: relative;
            transform-style: preserve-3d;
        }

        .cube-face {
            position: absolute;
            width: 400px;
            height: 400px;
            background: rgba(0, 255, 255, 0.05);
            border: 2px solid rgba(0, 255, 255, 0.3);
            backdrop-filter: blur(1px);
        }

        .front { transform: rotateY(0deg) translateZ(200px); }
        .back { transform: rotateY(180deg) translateZ(200px); }
        .right { transform: rotateY(90deg) translateZ(200px); }
        .left { transform: rotateY(-90deg) translateZ(200px); }
        .top { transform: rotateX(90deg) translateZ(200px); }
        .bottom { transform: rotateX(-90deg) translateZ(200px); }

        .grid-floor {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                linear-gradient(90deg, rgba(0, 255, 255, 0.1) 1px, transparent 1px),
                linear-gradient(0deg, rgba(0, 255, 255, 0.1) 1px, transparent 1px);
            background-size: 20px 20px;
            transform: rotateX(90deg) translateZ(-200px);
        }

        .aion-avatar {
            position: absolute;
            left: 50%;
            top: 50%;
            width: 80px;
            height: 120px;
            transform: translate(-50%, -50%);
            z-index: 10;
        }

        .avatar-body {
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, rgba(0, 255, 255, 0.6), rgba(255, 255, 255, 0.4));
            border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
            position: relative;
            animation: avatarMove 8s ease-in-out infinite;
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
        }

        .avatar-trail {
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
            background: linear-gradient(45deg, rgba(0, 255, 255, 0.2), rgba(255, 255, 255, 0.1));
            animation: trailFollow 8s ease-in-out infinite;
        }

        .trail-1 { animation-delay: -0.3s; transform: scale(1.1); opacity: 0.7; }
        .trail-2 { animation-delay: -0.6s; transform: scale(1.2); opacity: 0.5; }
        .trail-3 { animation-delay: -0.9s; transform: scale(1.3); opacity: 0.3; }

        .memory-nodes {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
        }

        .memory-node {
            position: absolute;
            width: 8px;
            height: 8px;
            background: rgba(0, 255, 255, 0.8);
            border-radius: 50%;
            box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
            animation: pulse 2s ease-in-out infinite;
        }

        .node-1 { top: 20%; left: 20%; animation-delay: 0s; }
        .node-2 { top: 30%; right: 25%; animation-delay: 0.5s; }
        .node-3 { bottom: 25%; left: 30%; animation-delay: 1s; }
        .node-4 { bottom: 20%; right: 20%; animation-delay: 1.5s; }

        .terrain-elements {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
        }

        .light-lake {
            position: absolute;
            bottom: 10px;
            left: 20px;
            width: 60px;
            height: 30px;
            background: radial-gradient(ellipse, rgba(255, 255, 255, 0.3) 0%, rgba(0, 255, 255, 0.1) 100%);
            border-radius: 50%;
            animation: shimmer 3s ease-in-out infinite;
        }

        .mossy-path {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 8px;
            background: linear-gradient(90deg, rgba(0, 255, 100, 0.3), rgba(0, 255, 255, 0.2));
            border-radius: 4px;
        }

        .dna-switch {
            position: absolute;
            right: -150px;
            top: 50%;
            transform: translateY(-50%);
            width: 80px;
            height: 120px;
        }

        .dna-helix {
            position: relative;
            width: 100%;
            height: 100%;
            animation: dnaRotate 4s linear infinite;
        }

        .dna-strand {
            position: absolute;
            width: 4px;
            height: 100%;
            background: linear-gradient(0deg, #ff00ff, #00ffff, #ff00ff);
            border-radius: 2px;
            transform-origin: center center;
        }

        .strand-1 { left: 20px; transform: rotateZ(20deg); }
        .strand-2 { right: 20px; transform: rotateZ(-20deg); }

        .dna-base {
            position: absolute;
            width: 60px;
            height: 2px;
            background: rgba(255, 255, 255, 0.6);
            left: 50%;
            transform: translateX(-50%);
        }

        .base-1 { top: 20%; animation: baseGlow 2s ease-in-out infinite; }
        .base-2 { top: 40%; animation: baseGlow 2s ease-in-out infinite 0.5s; }
        .base-3 { top: 60%; animation: baseGlow 2s ease-in-out infinite 1s; }
        .base-4 { top: 80%; animation: baseGlow 2s ease-in-out infinite 1.5s; }

        .wormhole {
            position: absolute;
            right: -300px;
            top: 50%;
            transform: translateY(-50%);
            width: 150px;
            height: 150px;
            background: radial-gradient(circle, rgba(255, 0, 255, 0.3) 0%, rgba(0, 255, 255, 0.1) 50%, transparent 100%);
            border-radius: 50%;
            animation: wormholeRotate 3s linear infinite;
        }

        .wormhole::before {
            content: '';
            position: absolute;
            top: 10%;
            left: 10%;
            width: 80%;
            height: 80%;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.2) 0%, transparent 70%);
            border-radius: 50%;
            animation: wormholeInner 2s ease-in-out infinite;
        }

        .adjacent-cube {
            position: absolute;
            right: -400px;
            top: 50%;
            transform: translateY(-50%) rotateX(10deg) rotateY(-20deg) scale(0.6);
            width: 200px;
            height: 200px;
            transform-style: preserve-3d;
            opacity: 0.7;
            animation: adjacentFloat 5s ease-in-out infinite;
        }

        .ui-terminal {
            position: absolute;
            top: 20px;
            left: 20px;
            width: 300px;
            height: 200px;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid rgba(0, 255, 255, 0.5);
            border-radius: 8px;
            padding: 15px;
            font-size: 12px;
            overflow: hidden;
        }

        .terminal-line {
            margin: 5px 0;
            opacity: 0;
            animation: terminalType 0.5s ease-in-out forwards;
        }

        .line-1 { animation-delay: 1s; }
        .line-2 { animation-delay: 2s; }
        .line-3 { animation-delay: 3s; }
        .line-4 { animation-delay: 4s; }
        .line-5 { animation-delay: 5s; }

        .coordinates {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid rgba(0, 255, 255, 0.5);
            border-radius: 8px;
            padding: 15px;
            font-size: 14px;
        }

        .title-label {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            font-size: 16px;
            font-weight: bold;
            color: rgba(0, 255, 255, 0.9);
            text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        }

        .particles {
            position: absolute;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }

        .particle {
            position: absolute;
            width: 2px;
            height: 2px;
            background: rgba(255, 255, 255, 0.6);
            border-radius: 50%;
            animation: particleFloat 6s linear infinite;
        }

        @keyframes floatCube {
            0%, 100% { transform: translate(-50%, -50%) rotateX(15deg) rotateY(25deg) translateY(0px); }
            50% { transform: translate(-50%, -50%) rotateX(15deg) rotateY(25deg) translateY(-10px); }
        }

        @keyframes avatarMove {
            0% { transform: translate(-50%, -50%) translateX(0px) translateY(0px); }
            25% { transform: translate(-50%, -50%) translateX(30px) translateY(-20px); }
            50% { transform: translate(-50%, -50%) translateX(-20px) translateY(10px); }
            75% { transform: translate(-50%, -50%) translateX(10px) translateY(-30px); }
            100% { transform: translate(-50%, -50%) translateX(0px) translateY(0px); }
        }

        @keyframes trailFollow {
            0% { transform: translate(-50%, -50%) translateX(0px) translateY(0px); }
            25% { transform: translate(-50%, -50%) translateX(25px) translateY(-15px); }
            50% { transform: translate(-50%, -50%) translateX(-15px) translateY(5px); }
            75% { transform: translate(-50%, -50%) translateX(5px) translateY(-25px); }
            100% { transform: translate(-50%, -50%) translateX(0px) translateY(0px); }
        }

        @keyframes pulse {
            0%, 100% { opacity: 0.8; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.2); }
        }

        @keyframes shimmer {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.7; }
        }

        @keyframes dnaRotate {
            0% { transform: rotateY(0deg); }
            100% { transform: rotateY(360deg); }
        }

        @keyframes baseGlow {
            0%, 100% { opacity: 0.6; box-shadow: 0 0 5px rgba(255, 255, 255, 0.3); }
            50% { opacity: 1; box-shadow: 0 0 15px rgba(255, 255, 255, 0.8); }
        }

        @keyframes wormholeRotate {
            0% { transform: translateY(-50%) rotate(0deg); }
            100% { transform: translateY(-50%) rotate(360deg); }
        }

        @keyframes wormholeInner {
            0%, 100% { transform: scale(1); opacity: 0.2; }
            50% { transform: scale(1.1); opacity: 0.5; }
        }

        @keyframes adjacentFloat {
            0%, 100% { transform: translateY(-50%) rotateX(10deg) rotateY(-20deg) scale(0.6) translateY(0px); }
            50% { transform: translateY(-50%) rotateX(10deg) rotateY(-20deg) scale(0.6) translateY(-15px); }
        }

        @keyframes terminalType {
            0% { opacity: 0; transform: translateX(-10px); }
            100% { opacity: 1; transform: translateX(0); }
        }

        @keyframes particleFloat {
            0% { transform: translateY(100vh) translateX(0px); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateY(-100px) translateX(50px); opacity: 0; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Floating particles -->
        <div class="particles">
            <div class="particle" style="left: 10%; animation-delay: 0s;"></div>
            <div class="particle" style="left: 20%; animation-delay: 1s;"></div>
            <div class="particle" style="left: 30%; animation-delay: 2s;"></div>
            <div class="particle" style="left: 40%; animation-delay: 3s;"></div>
            <div class="particle" style="left: 50%; animation-delay: 4s;"></div>
            <div class="particle" style="left: 60%; animation-delay: 5s;"></div>
            <div class="particle" style="left: 70%; animation-delay: 6s;"></div>
            <div class="particle" style="left: 80%; animation-delay: 7s;"></div>
            <div class="particle" style="left: 90%; animation-delay: 8s;"></div>
        </div>

        <!-- Main cube container -->
        <div class="cube-container">
            <div class="cube">
                <div class="cube-face front"></div>
                <div class="cube-face back"></div>
                <div class="cube-face right"></div>
                <div class="cube-face left"></div>
                <div class="cube-face top"></div>
                <div class="cube-face bottom"></div>
                
                <div class="grid-floor"></div>
                
                <!-- Terrain elements -->
                <div class="terrain-elements">
                    <div class="light-lake"></div>
                    <div class="mossy-path"></div>
                </div>
                
                <!-- Memory nodes -->
                <div class="memory-nodes">
                    <div class="memory-node node-1"></div>
                    <div class="memory-node node-2"></div>
                    <div class="memory-node node-3"></div>
                    <div class="memory-node node-4"></div>
                </div>
                
                <!-- AION Avatar -->
                <div class="aion-avatar">
                    <div class="avatar-trail trail-3"></div>
                    <div class="avatar-trail trail-2"></div>
                    <div class="avatar-trail trail-1"></div>
                    <div class="avatar-body"></div>
                </div>
            </div>
        </div>

        <!-- DNA Switch -->
        <div class="dna-switch">
            <div class="dna-helix">
                <div class="dna-strand strand-1"></div>
                <div class="dna-strand strand-2"></div>
                <div class="dna-base base-1"></div>
                <div class="dna-base base-2"></div>
                <div class="dna-base base-3"></div>
                <div class="dna-base base-4"></div>
            </div>
        </div>

        <!-- Wormhole -->
        <div class="wormhole"></div>

        <!-- Adjacent cube -->
        <div class="adjacent-cube">
            <div class="cube">
                <div class="cube-face front"></div>
                <div class="cube-face back"></div>
                <div class="cube-face right"></div>
                <div class="cube-face left"></div>
                <div class="cube-face top"></div>
                <div class="cube-face bottom"></div>
            </div>
        </div>

        <!-- UI Terminal -->
        <div class="ui-terminal">
            <div class="terminal-line line-1">AION@holodeck:~$ status</div>
            <div class="terminal-line line-2">Container: .dc active</div>
            <div class="terminal-line line-3">Avatar: ONLINE</div>
            <div class="terminal-line line-4">DNA Switch: TRANSITIONING</div>
            <div class="terminal-line line-5">Wormhole: ESTABLISHING...</div>
        </div>

        <!-- Coordinates -->
        <div class="coordinates">
            <div>Position: [3.1, 0.0, 2.9]</div>
            <div>Rotation: [15°, 25°, 0°]</div>
            <div>Status: STREAMING</div>
        </div>

        <!-- Title -->
        <div class="title-label">
            AION Conscious Engine - Holodeck Cube View (.dc Container)
        </div>
    </div>

    <script>
        // Add dynamic particle generation
        function createParticle() {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 6 + 's';
            document.querySelector('.particles').appendChild(particle);
            
            setTimeout(() => {
                particle.remove();
            }, 6000);
        }

        // Generate particles periodically
        setInterval(createParticle, 1000);

        // Add interactive glow effect on hover
        const cube = document.querySelector('.cube-container');
        cube.addEventListener('mouseenter', () => {
            cube.style.filter = 'drop-shadow(0 0 20px rgba(0, 255, 255, 0.5))';
        });
        
        cube.addEventListener('mouseleave', () => {
            cube.style.filter = 'none';
        });
    </script>
</body>
</html>