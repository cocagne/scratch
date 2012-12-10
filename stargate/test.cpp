
#include <iostream>

#include "t.hpp"

#include "abidos.hpp"

using namespace std;

using namespace test_world;

void test_cb( sg::PObject obj )
{
   cerr << "%%% CALLBACK FUNCTION!! %%%" << endl;
}

void test2_cb( const VehicleObject & v )
{
   cerr << "%%%%% EXACT CALLBACK %%%%" << endl;
   cerr << "   FQ Latitude: " << v.getInstance().loc().pos().longitude() << endl;
}


int main(void)
{
   sg::PWorld world;
   sg::PWorldInterface wi;
   sg::PWorldInterface wi2;
    
   try
   {
      world = abidos::load_world( "FooWorld", "/home/thomas.cocagne/devel/stargate/test_world.wdf" );

      wi = abidos::createWorldInterface( "test_iface", world );

      wi2 = abidos::createWorldInterface( "test_iface2", world );

      if (!wi || !wi2)
      {
         cerr << "Failed to create world interface!!!" << endl;
         return 0;
      }
   } 
   catch (abidos::LoadError & e)
   {
      cerr << "Failed to load world!: " << e.what() << endl;
      return 0;
   }

//    return 0;
    
   cerr << "************ World Types *************" << endl;
    
   world->printTypes();
    
   cerr << "**************************************" << endl;
    
    
   //PhysicalEntityObject po = wi->createObject<PhysicalEntityObject>();

   wi2->setNewObjectHandler( PhysicalEntity::ID, test_cb );
   
   wi2->setNewObjectHandler< VehicleObject >( test2_cb );
   
   cerr << " %% Running Callbacks (should be empty) %% " << endl;
   
   wi2->runCallbacks();
   
   AircraftObject po = wi->createObject<AircraftObject>();
    
   cerr << "******* object created ********" << endl;

   cerr << "FQ Latitude: " << po.getInstance().loc().pos().longitude() << endl;
    
   PhysicalEntity pe = po.getInstance();
    
   cerr << "Got Instance" << endl;
    
   Location l = pe.loc();
    
   cerr << "Got Location" << endl;
    
   Position p = l.pos();
    
   cerr << "Got Position" << endl;
    
   cerr << "Lat, lon, alt = " << p.latitude() << ", " << p.longitude() << ", " << p.altitude() << endl;
    
   p.latitude( 3.14159 );
        
   cerr << "Lat, lon, alt = " << p.latitude() << ", " << p.longitude() << ", " << p.altitude() << endl;

   // String test
   Aircraft a = po.getInstance();

   cerr << "Callsign: " << (const char *) (a.callsign()->data()) << endl;

   a.callsign( "Foo Bar" );

   cerr << "Callsign: " << (const char *) (a.callsign()->data()) << endl;

   cerr << " %% Running Callbacks (should see 1) %% " << endl;
   wi2->runCallbacks();
    
   return 0;
}
