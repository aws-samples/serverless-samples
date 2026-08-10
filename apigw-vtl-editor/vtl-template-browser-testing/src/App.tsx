import { AppLayout, SpaceBetween } from '@cloudscape-design/components';
import '@cloudscape-design/global-styles/index.css';
import ApiGatewayHttpSimulator from './components/ApiGatewayHttpSimulator';

function App() {
  return (
    // <AppLayout
    //   content={
    //     <SpaceBetween direction="vertical" size="l">
    //       <ApiGatewayHttpSimulator />
    //     </SpaceBetween>
    //   }
    //   navigationHide
    //   toolsHide
    // />
    <ApiGatewayHttpSimulator />
  );
}

export default App;
